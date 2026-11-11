import pandas as pd
import tomllib
from datetime import datetime
from typing import Any
import re
import uuid
import psycopg
import os
import click
from dotenv import load_dotenv

OUT_DIRECTORY = "./pipeline/out/"
# No file extension
OUT_FILE_NAME = "out"
REJECTED_FILE_NAME = "rejected"


TYPE_MAP : dict[str, Any] = {
	"str": str,
	"date": datetime.date,
	"time": datetime.time,
	"None": type(None),
	"datetime": datetime
}

specs_file = open("./pipeline/spec.toml", "rb")
specs = tomllib.load(specs_file)

if not specs['column-types']: 
	raise IndexError('No column-types header')
if not isinstance(specs['column-types'], dict):
	raise TypeError('column-types must be a dictionary')
if not specs['column-types']['first']:
	raise IndexError('No column-types.first field')
if not isinstance(specs['column-types']['first'], dict):
	raise TypeError('column-types.first must be a dict')
if not specs['valid-type-values']:
	raise IndexError('Missing valid-type-values header')
if not isinstance(specs["valid-type-values"], dict):
	raise TypeError('Wrong type for valid-type-values')
if not specs["valid-mode-values"]:
	raise IndexError("Missing valid-mode-values")
if not isinstance(specs["valid-mode-values"], list):
	t = type(specs['valid-mode-values'])
	raise TypeError(f"Wrong type for valid-mode-values, expected list, got {t}")
if not specs['entity-colapse-map']:
	raise IndexError("Missing entity-colapse-map")
if not isinstance(specs["entity-colapse-map"], dict):
	raise TypeError(f"Wrong type for entity-colapse-map, expected dict, got {type(specs["entity-colapse-map"])}")

def load_file(path : str, sheet : str = "0") -> pd.DataFrame:
   df: pd.DataFrame = pd.read_excel( # type: ignore[reportUnknownMemberType]
      path,
      sheet_name=sheet,
      engine='openpyxl'
   )
   return df

def is_meeting_link(link: str) -> bool:
	if re.match(r"https://teams.microsoft.com/.*", link):
		return True

	if re.match(r"https://events.teams.microsoft.com/.*", link):
		return True
	return False

def verify_fields(df : pd.DataFrame) -> pd.DataFrame:
   for column_name, types_expr in specs['column-types']['first'].items():
      if not isinstance(column_name, str):
         raise TypeError('idk')
      if not isinstance(types_expr, str):
         raise TypeError('Not a valid type.')
      type_names = types_expr.split('|')

      types = [t for tn, t in TYPE_MAP.items() if tn in type_names] # Nuke python pls

      if len(types) == 0:
         raise TypeError(f"{types_expr} are not valid types.")

      if column_name not in df.columns:
         raise IndexError(f"{column_name} is not present in the file.")
      
      for typ in types:
         if typ == datetime.date:
            df[column_name] = pd.to_datetime(df[column_name], errors='coerce', format="%Y-%m-%d")
            continue
         if typ == datetime.time:
            df[column_name] = pd.to_datetime(df[column_name], errors='coerce', format="%H:%M")
            continue
         if typ == str: continue
         if typ == type(None): continue
         raise TypeError(f"{column_name} is not compliant with the specs.")
   return df

def validate_values_row(row : pd.Series) -> pd.Series | None:
	start_date : datetime = row["Fecha inicio"]
	start_time : datetime = row["Hora inicio"]
	end_date : datetime = row["Fecha fin"]
	end_time : datetime = row["Hora fin"]
	start_datetime = datetime.now()
	end_datetime = datetime.now()
	
	try:
		start_datetime = datetime(
			start_date.year, 
			start_date.month, 
			start_date.day, 
			start_time.hour, 
			start_time.minute, 
			start_time.second
			)
	except:
		return None
	try:
		end_datetime = datetime(
			end_date.year, 
			end_date.month, 
			end_date.day, 
			end_time.hour, 
			end_time.minute, 
			end_time.second
		)
	except:
		return None

	activity_type = row["Actividad"]
	if not activity_type:
		return None

	place : str | None = row["Salón"]
	link : str | None  = row["Enlace"]

	mode : str | None = row["Tipo"]
	if not mode:
		return None

	if mode.strip().lower() not in specs["valid-mode-values"]:
		return None

	mode = mode.strip().lower()

	if mode.lower() == "presencial":
		if not place:
			return None
		mode = mode.lower()

	if mode.lower() == "virtual":
		if not link:
			return None

		if not is_meeting_link(link):
			return None
		
		mode = mode.lower()

	title = row["Título"]
	if not title:
		return None

	presentator: str | None = row["Ponente"]
	entity: str | None = row["Empresa / Institución"]
	master: str | None = row["Maestro de ceremonias"]

	# Redundante
	# if master and presentator:
	# 	if master == presentator:
	# 		print(f"same master and presentator {master} = {presentator}")
	# 		return None

	data : dict[str, datetime | str | None] = {
		"start": start_datetime,
		"end": end_datetime,
		"title": title,
		"place": place,
		"link": link,
		"mode": mode,
		"type": activity_type,
		"presentator": presentator,
		"master": master,
		"entity": entity
	}

	return pd.Series(data)
	
def validate_values(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rejected_list : list[Any] = []
    new_list : list[Any] = []
    
    for _, row in df.iterrows():
        new_row = validate_values_row(row)
        if new_row is None:
            rejected_data : dict[str, Any] = {
                "start": f"{row['Fecha inicio']} {row['Hora inicio']}",
                "end": f"{row['Fecha fin']} {row['Hora fin']}",
                "title": row["Título"],
                "place": row["Salón"],
                "link": row["Enlace"],
                "mode": row["Tipo"],
                "type": row["Actividad"],
                "presentator": row["Ponente"],
                "master": row["Maestro de ceremonias"],
                "entity": row["Empresa / Institución"]
            }
            rejected_list.append(rejected_data)
            continue
            
        new_list.append(new_row)
        
    rejected = pd.DataFrame(rejected_list)
    new = pd.DataFrame(new_list)
    
    return (new, rejected)

presentator_split_pattern = r"\s*(?:,|\/|\by\b)\s*"
invalid_presentators = specs["invalid_presentators"]

def parse_presentators(presentators : str) -> list[str]:

	if presentators in invalid_presentators:
		return []

	names = re.split(presentator_split_pattern, presentators)
	# Quita cadenas vacias
	return [n for n in names if n and n not in invalid_presentators]

# Principal
room_pattern = r"^(?P<campus>CUAUH|CU)?\s*(?P<building>[A-Z]\d?)\b\s*(?P<room>\d*)"
# Fallback
campus_pattern = r"^(?P<campus>CUAUH|CU) .*$"

def parse_row(row : pd.Series) -> pd.Series:

	raw_activity_type = row.get("type", "")

	if not isinstance(raw_activity_type, str):
		raw_activity_type = ""

	activity_type : str = raw_activity_type.strip()
	
	if activity_type.lower() not in specs["valid-type-values"]:
		activity_type = 'otra'

	activity_type = activity_type.lower()

	place : str = row.get("place", "").strip()

	match = re.search(room_pattern, place)
	campus : str | None = None
	building : str | None = None
	room : str | None = None

	if match is not None:
		campus = match.group("campus") or specs["default_campus"]
		building = match.group("building")
		room = match.group("room")
	else:
		m = re.search(campus_pattern, place)
		if m is not None:
			campus = m.group("campus")
		else:
			campus = "IIT"

	c_presentator : str | None = row.get("presentator")
	presentators = []
	if isinstance(c_presentator, str):
		presentators = parse_presentators(c_presentator.strip())

	# ! Aun falta implementar para colapsar las entidades ej (Universidad Autonoma de Ciudad Juarez -> UACJ)
	
	row["presentator"] = presentators
	row["building"] = building
	row["room"] = room
	row["campus"] = campus
	row["type"] = activity_type

	return row

def parse_values(df : pd.DataFrame) -> pd.DataFrame:
	result_df = df.apply(parse_row, axis=1)
	return result_df

# def get_distinc_presentators(df) -> list[str]:
# 	l = []
# 	for presentator in df["presentator"]:
# 		for p in presentator	:
# 			if p not in l:
# 				l.append(p)
# 	return l

# def get_distinc_masters(df) -> list[str]:
# 	l = []
# 	for master in df["master"]:
# 		if master not in l:
# 			l.append(master)
# 	return l

unusual_entity_names : list[str] = []

def norm_row(row : pd.Series) -> pd.Series:
	ent_name = row["entity"]
	known = False
	for i, v in specs['entity-colapse-map'].items():
		if i == ent_name:
			known = True
			break
		if ent_name in  v:
			ent_name = i
			known = True

	if not known and ent_name not in unusual_entity_names:
		unusual_entity_names.append(ent_name)

	row["entity"] = ent_name
	
	return row

def normalize_values(df : pd.DataFrame) -> pd.DataFrame:
	return df.apply(norm_row, axis=1)

class Location:
	id : uuid.UUID
	session : uuid.UUID
	link : str | None
	def __init__(self, id : uuid.UUID, session : uuid.UUID, link : str | None) -> None:
		self.id = id
		self.session = session
		self.link = link

class Room:
	campus : str
	building : str
	room : str
	def __init__(self, id, campus, building, room) -> None:
		self.id = id
		self.campus = campus
		self.building = building
		self.room = room

	def __eq__(self, value: object) -> bool:
		if not isinstance(value, Room):
			return False

		if self.campus == value.campus and self.building == value.building and self.room == value.room:
			return True

		return False

class RoomLocation (Location):
	room : Room

	def __init__(self, id: uuid.UUID, session: uuid.UUID, link: str | None, room : Room) -> None:
		super().__init__(id, session, link)
		self.room = room

class RandomLocation (Location):
	description : str
	def __init__(self, id : uuid.UUID, session : uuid.UUID, link : str | None, desc : str) -> None:
		self.id = id
		self.session = session
		self.link = link
		self.description = desc

class Person:
	id : uuid.UUID
	name : str
	def __init__(self, id : uuid.UUID, name : str) -> None:
		self.id = id
		self.name = name
	def __eq__(self, value: object) -> bool:
		if not isinstance(value, Person):
			return False

		if value.name == self.name:
			return True

		return False

class Entity:
	id: uuid.UUID
	name : str
	def __init__(self, id : uuid.UUID, name : str) -> None:
		self.id = id
		self.name = name

	def __eq__(self, value: object) -> bool:
			if not isinstance(value, Entity):
				return False
	
			if value.name == self.name:
				return True
	
			return False

class Event:
	id : uuid.UUID
	title : str
	entity : Entity
	master : Person
	type : str

	def __init__(self, id : uuid.UUID, title : str, entity : Entity, master : Person, type : str) -> None:
		self.id = id
		self.title = title
		self.entity = entity
		self.master = master

		if specs["valid-type-values"][type]:
			self.type = type
		else:
			raise TypeError(f"Wrong event type!, {type} is no a valid type.")

class Session:
	id : uuid.UUID
	starts : datetime
	ends : datetime
	event : Event
	def __init__(self, id:uuid.UUID, starts:datetime, ends:datetime, event:Event) -> None:
		self.id = id
		self.starts = starts
		self.ends = ends
		self.event = event

# No es muy util afuera de este script
def find[T](hay : list[T], needle: T) -> T | None:
	for v in hay:
		if v == needle:
			return v

def load_to_database(df : pd.DataFrame, purge_db : bool):
	random_locations : list[RandomLocation] = []
	room_locations : list[RoomLocation] = []
	virtual_locations : list[Location] = []
	persons : list[Person] = []
	events : list[Event] = []
	sessions : list[Session] = []
	entities : list[Entity] = []
	rooms : list[Room] = []

	for i, row in df.iterrows():
		start : datetime = row['start']
		end : datetime = row['end']
		title : str = row['title']
		place : str = row['place']
		link : str = row['link']
		act_type : str = row['type']
		presentator : list[str] = row['presentator']
		master : str = row['master']
		entity_str : str = row['entity']
		building : str | None = row['building']
		room : str | None = row['room']
		campus : str = row['campus']

		ps : list[Person] = []
		master_o : Person | None = None
		location : RandomLocation | Location | Room | None = None
		session_id = uuid.uuid7()

		if master:
			master_o = Person(uuid.uuid7(), master)
			f = find(persons, master_o)
			if f:
				master_o = f
			else:
				persons.append(master_o)

		assert(master_o)
		
		for n in presentator:
			p = Person(uuid.uuid7(), n)
			f = find(persons, p)
			if f:
				ps.append(f)
			else:
				ps.append(p)
				persons.append(p)

		if building and room:
			room_o = Room(uuid.uuid7(), campus, building, room)
			_f = find(rooms, room_o)
			if _f:
				room_o = _f

			location = RoomLocation(uuid.uuid7(), session_id, link, room_o)

			room_locations.append(location)
		elif not place and link:
			location = Location(uuid.uuid7(), session_id, link)
			virtual_locations.append(location)
		else:
			location = RandomLocation(uuid.uuid7(), session_id, link, place)
			random_locations.append(location)

		entity = Entity(uuid.uuid7(), entity_str)

		_f = find(entities, entity)

		if _f:
			entity = _f
		else:
			entities.append(entity)

		event = Event(uuid.uuid7(), title, entity, master_o, act_type)
		session = Session(session_id, start, end, event)

		events.append(event)
		sessions.append(session)

	conn = psycopg.connect(DB_URL)
	cursor = conn.cursor()

	if purge_db:
		pass

# PIPELINE!
df = load_file("./pipeline/input_data.xlsx", "Actividades")
df = verify_fields(df)
(df, rejected) = validate_values(df)
df = parse_values(df)
df = normalize_values(df)

print(f"Rejected {len(rejected)} rows, saved to {OUT_DIRECTORY + REJECTED_FILE_NAME + ".*"}")

if click.confirm("Save to outfiles?", default=True):
	try:
		os.mkdir(OUT_DIRECTORY)
	except FileExistsError:
		pass
	except Exception as e:
		print(f"Could not create directory {OUT_DIRECTORY}: {e}")
		exit()

	rejected.to_csv(OUT_DIRECTORY + REJECTED_FILE_NAME + ".csv")
	rejected.to_excel(OUT_DIRECTORY + REJECTED_FILE_NAME + ".xlsx", sheet_name="Actividades")
	df.to_csv(OUT_DIRECTORY + OUT_FILE_NAME + ".csv", index=False)
	df.to_excel(OUT_DIRECTORY + OUT_FILE_NAME + ".xlsx", sheet_name="Actividades")

if click.confirm("Save to database? (can't undo)", default=False):
	print("Whoops, im still implementing that.")
	exit()

	load_dotenv()

	DB_URL = os.getenv("DATABASE_URL", "")

	if DB_URL is None:
		raise EnvironmentError("MISSING DATABASE_URL")

	load_to_database(df, click.confirm("Purge database? (Risky)", default=False))