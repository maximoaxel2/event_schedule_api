use chrono::{DateTime, Local};
use serde::{Serialize, Deserialize};
use sqlx::{FromRow, Type};
use sqlx::types::Json;
use uuid::Uuid;

#[derive(Serialize, FromRow)]
pub struct Session {
    pub id: Uuid,
    
    #[sqlx(flatten)] 
    pub event: Event,
    
    pub starts: DateTime<Local>,
    pub ends: DateTime<Local>,
    pub mode: EventMode,
    pub presentators: Option<Json<Vec<Person>>>, 
    pub location: Option<Json<Location>>
}

#[derive(Serialize, FromRow)]
#[serde(rename_all="kebab-case")]
pub struct Event {
    #[sqlx(rename = "event_id")]
    pub id: Uuid,
    pub title: String,
    pub entity: Option<Json<Entity>>,
    pub master: Option<Json<Person>>,
    pub event_type: EventType, 
}

#[derive(Serialize, Deserialize, FromRow, Debug)] 
pub struct Person {
    pub id: Uuid,
    pub name: String,
}

#[derive(Serialize, Deserialize, FromRow, Debug)]
pub struct Entity {
    pub id: Uuid,
    pub name: String,
}

#[derive(Serialize, Deserialize, FromRow, Debug)]
pub struct Location {
    pub id: Uuid,
    pub session: Uuid,
    pub link: Option<String>,
    pub room: Option<Room>, 
    pub description: Option<String>,
}

#[derive(Serialize, Deserialize, FromRow, Debug)]
pub struct Room {
    pub id: Uuid, 
    pub campus: String,
    pub building: String,
    pub room: String,
    pub sub: Option<String>,
}

#[derive(Deserialize, Serialize, Debug, PartialEq, Type)]
#[serde(rename_all = "lowercase")] 
#[sqlx(type_name = "event_mode", rename_all = "lowercase")]
pub enum EventMode {
    Presencial,
    Virtual,
    Hibrido,
}

#[derive(Deserialize, Serialize, Debug, PartialEq, Type)]
#[serde(rename_all = "lowercase")] 
#[sqlx(type_name = "event_type", rename_all = "lowercase")] 
pub enum EventType {
    Conferencia,
    Taller,
    Foro,
    Concurso,
    Ponencia,
    
    #[serde(rename = "presentación")]
    #[sqlx(rename = "presentación")]
    Presentacion,
    
    Curso,
    Deportiva,
    Cultural,
    Otra,
    
    #[serde(rename = "conferencia magistral")]
    #[sqlx(rename = "conferencia magistral")]
    ConferenciaMagistral,
    
    #[serde(rename = "visita de campo")]
    #[sqlx(rename = "visita de campo")]
    VisitaDeCampo,
    
    Panel,
    Exposicion, 
    
    #[serde(rename = "cátedra patrimonial")]
    #[sqlx(rename = "cátedra patrimonial")]
    CatedraPatrimonial,
    
    #[serde(rename = "mesa de diálogo")]
    #[sqlx(rename = "mesa de diálogo")]
    MesaDeDialogo,
    
    #[serde(rename = "capacitación")]
    #[sqlx(rename = "capacitación")]
    Capacitacion
}