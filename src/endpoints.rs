use axum::{Json, extract::Query, response::IntoResponse};
use uuid::Uuid;
use chrono::{DateTime, Local};
use serde::{Deserialize};
use sqlx::{QueryBuilder, Postgres};

use crate::types;
use crate::database;
use crate::types::EventType;

#[derive(Deserialize)]
#[serde(rename_all = "kebab-case")]
pub struct SessionQuery {
   id : Option<Uuid>,
   #[serde(rename = "type")]
   activity_type : Option<EventType>,
   after : Option<DateTime<Local>>,
   before : Option<DateTime<Local>>,
   presentator : Option<String>,
   presentator_id : Option<Uuid>,
   title : Option<String>,
   master : Option<String>,
   master_id : Option<Uuid>,
   campus : Option<String>,
   mode : Option<types::EventMode>,
   entity : Option<String>,
   entity_id : Option<Uuid>
}

pub async fn get_sessions(Query(query): Query<SessionQuery>) -> impl IntoResponse {
    let db_pool = database::get_pool();
    let mut query_builder: QueryBuilder<Postgres> = 
        QueryBuilder::new("SELECT * FROM sessions_query WHERE 1=1");

    if let Some(id) = query.id {
        query_builder.push(" AND id = ");
        query_builder.push_bind(id);
    }

    if let Some(activity_type) = query.activity_type {
        query_builder.push(" AND event_type = ");
        query_builder.push_bind(activity_type);
    }

    if let Some(after) = query.after {
        query_builder.push(" AND starts >= ");
        query_builder.push_bind(after);
    }

    if let Some(before) = query.before {
        query_builder.push(" AND ends <= ");
        query_builder.push_bind(before);
    }

    if let Some(presentator) = query.presentator {
        query_builder.push(" AND ");
        query_builder.push_bind(presentator);
    }

    if let Some(presentator_id) = query.presentator_id {
        query_builder.push(" AND presentator_id = ");
        query_builder.push_bind(presentator_id);
    }

    if let Some(title) = query.title {
        query_builder.push(" AND title ILIKE ");
        query_builder.push_bind(format!("%{}%", title));
    }

    if let Some(master) = query.master {
        query_builder.push(" AND master ILIKE ");
        query_builder.push_bind(format!("%{}%", master));
    }

    if let Some(master_id) = query.master_id {
        query_builder.push(" AND master_id = ");
        query_builder.push_bind(master_id);
    }

    if let Some(campus) = query.campus {
        query_builder.push(" AND campus ILIKE ");
        query_builder.push_bind(format!("%{}%", campus));
    }

    if let Some(mode) = query.mode {
        query_builder.push(" AND mode = ");
        query_builder.push_bind(mode);
        query_builder.push("::event_mode"); 
    }

    if let Some(entity) = query.entity {
        query_builder.push(" AND entity ILIKE ");
        query_builder.push_bind(format!("%{}%", entity));
    }

    if let Some(entity_id) = query.entity_id {
		query_builder.push(" AND e.id = ");
		query_builder.push_bind(entity_id);
	}

    match query_builder.build_query_as::<types::Session>().fetch_all(db_pool).await {
        Ok(sessions) => Json(sessions).into_response(),
        Err(e) => {
            eprintln!("Database query failed: {:?}", e);
            axum::http::StatusCode::INTERNAL_SERVER_ERROR.into_response()
        }
    }
}