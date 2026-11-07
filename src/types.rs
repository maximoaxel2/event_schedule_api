use chrono::{DateTime, Utc};
use serde::{Serialize, Deserialize};
use sqlx::{FromRow, Type};
use sqlx::types::Json;
use uuid::Uuid;
use utoipa::ToSchema;

#[derive(Serialize, FromRow, ToSchema)]
pub struct Session {
    pub id: Uuid,
    
    #[sqlx(flatten)] 
    pub event: Event,
    
    pub starts: DateTime<Utc>,
    pub ends: DateTime<Utc>,
    pub mode: EventMode,
    
    // Tell Utoipa to document this as an Option<Vec<Person>>
    #[schema(value_type = Option<Vec<Person>>)] 
    pub presentators: Option<Json<Vec<Person>>>, 
    
    #[schema(value_type = Option<Location>)]
    pub location: Option<Json<Location>>
}

#[derive(Serialize, FromRow, ToSchema)]
#[serde(rename_all="kebab-case")]
pub struct Event {
    #[sqlx(rename = "event_id")]
    pub id: Uuid,
    pub title: String,
    
    #[schema(value_type = Option<Entity>)]
    pub entity: Option<Json<Entity>>,
    
    #[schema(value_type = Option<Person>)]
    pub master: Option<Json<Person>>,
    
    pub event_type: EventType, 
}
#[derive(Serialize, Deserialize, FromRow, Debug, ToSchema)] 
pub struct Person {
    pub id: Uuid,
    pub name: String,
}

#[derive(Serialize, Deserialize, FromRow, Debug, ToSchema)]
pub struct Entity {
    pub id: Uuid,
    pub name: String,
}

#[derive(Serialize, Deserialize, FromRow, Debug, ToSchema)]
pub struct Location {
    pub id: Uuid,
    pub session: Uuid,
    pub link: Option<String>,
    pub room: Option<Room>, 
    pub description: Option<String>,
}

#[derive(Serialize, Deserialize, FromRow, Debug, ToSchema)]
pub struct Room {
    pub id: Uuid, 
    pub campus: String,
    pub building: String,
    pub room: String,
    pub sub: Option<String>,
}

#[derive(Deserialize, Serialize, Debug, PartialEq, Type, ToSchema)]
#[serde(rename_all = "lowercase")] 
#[sqlx(type_name = "event_mode", rename_all = "lowercase")]
pub enum EventMode {
    Presencial,
    Virtual,
    Hibrido,
}

#[derive(Deserialize, Serialize, Debug, PartialEq, Type, ToSchema)]
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