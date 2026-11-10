import pandas as pd
import tomllib
from datetime import datetime
from typing import Any
import re

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
		print("datetime")
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
		print("datetime")
		return None

	activity_type = row["Actividad"]
	if not activity_type:
		print("type")
		return None

	place : str | None = row["Salón"]
	link : str | None  = row["Enlace"]

	mode : str | None = row["Tipo"]
	if not mode:
		print("mode")
		return None

	if mode.lower() == "presencial":
		if not place:
			print("place")
			return None
		mode = mode.lower()

	if mode.lower() == "virtual":
		if not link:
			print("link")
			return None

		if not is_meeting_link(link):
			print("no valid link")
			return None
		
		mode = mode.lower()


	title = row["Título"]
	if not title:
		print("no title")
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
            print("no valid")
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
invalid_presentators = [
	"-",
	"N/A",
	"UACJ Campus IIT",
	"n.a" # No manchen quien puso n.a,
	"Alumnos proximos a egresar" # Este es un "hailmary"
]
def parse_presentators(presentators : str) -> list[str]:

	if presentators in invalid_presentators:
		return []

	names = re.split(presentator_split_pattern, presentators)
	# Quita cadenas vacias
	return [n for n in names if n]
		

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

	place : str = row.get("place", "").strip()

	match = re.search(room_pattern, place)
	campus : str | None = None
	building : str | None = None
	room : str | None = None

	if match is not None:
		campus = match.group("campus")
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

	row["presentator"] = presentators
	row["building"] = building
	row["room"] = room
	row["campus"] = campus
	row["type"] = activity_type

	return row

def parse_values(df : pd.DataFrame) -> pd.DataFrame:
	result_df = df.apply(parse_row, axis=1)
	return result_df

df = load_file("./pipeline/input_data.xlsx", "Actividades")
df = verify_fields(df)
(df, rejected) = validate_values(df)
df = parse_values(df)

df.to_csv("./pipeline/out.csv", index=False)

print(df['presentator'])