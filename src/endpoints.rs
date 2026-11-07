use axum::{Json, extract::Query, response::IntoResponse};
use chrono::Utc;
use chrono::{DateTime};
use serde::Deserialize;
use sqlx::{Postgres, QueryBuilder};
use utoipa::IntoParams;
use uuid::Uuid;

use crate::database;
use crate::types;
use crate::types::EventType;

#[derive(Deserialize, IntoParams)]
#[serde(rename_all = "kebab-case")]
#[into_params(parameter_in = Query, rename_all = "kebab-case")]
pub struct SessionQuery {
    /// Uuid for a specific session.
    id: Option<Uuid>,

    /// Type of activity.
    #[serde(rename = "type")]
    #[param(rename = "type")]
    activity_type: Option<EventType>,

    /// Events after. Unix timestamp.
    #[serde(default, with = "chrono::serde::ts_seconds_option")]
    #[param(value_type = Option<i64>)]
    after: Option<DateTime<Utc>>,

    /// Events before. Unix timestamp.
    #[serde(default, with = "chrono::serde::ts_seconds_option")]
    #[param(value_type = Option<i64>)]
    before: Option<DateTime<Utc>>,

    /// Search by presentator name
    presentator: Option<String>,
    /// Search by presentator uuid
    presentator_id: Option<Uuid>,

    /// Search by title.
    title: Option<String>,

    /// Search by master name.
    master: Option<String>,

    /// Saeach by master uuid.
    master_id: Option<Uuid>,

    /// Search by campus name.
    campus: Option<String>,

    /// Search by mode.
    mode: Option<types::EventMode>,

    /// Search by entity name.
    entity: Option<String>,

    /// Search by entity id.
    entity_id: Option<Uuid>,
}

#[utoipa::path(
    get,
    path = "/api/sessions",
    params(
        SessionQuery
    ),
    responses(
        (status = 200, description = "Successfully retrieved sessions", body = [types::Session]),
        (status = 500, description = "Internal Server Error")
    ),
    tag = "Sessions"
)]
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

    if let Some(presentator_name) = query.presentator {
        query_builder.push(" AND EXISTS (SELECT 1 FROM json_array_elements(COALESCE(presentators, '[]'::json)) p WHERE p->>'name' ILIKE ");
        query_builder.push_bind(format!("%{}%", presentator_name));
        query_builder.push(")");
    }

    if let Some(presentator_id) = query.presentator_id {
        query_builder
            .push(" AND presentators::jsonb @> jsonb_build_array(jsonb_build_object('id', ");
        query_builder.push_bind(presentator_id);
        query_builder.push("::uuid))");
    }

    if let Some(title) = query.title {
        query_builder.push(" AND title ILIKE ");
        query_builder.push_bind(format!("%{}%", title));
    }

    if let Some(master_id) = query.master_id {
        query_builder.push(" AND (master->>'id')::uuid = ");
        query_builder.push_bind(master_id);
    }

    if let Some(master_name) = query.master {
        query_builder.push(" AND master->>'name' ILIKE ");
        query_builder.push_bind(format!("%{}%", master_name));
    }

    if let Some(campus) = query.campus {
        query_builder.push(" AND location->'room'->>'campus' ILIKE ");
        query_builder.push_bind(format!("%{}%", campus));
    }

    if let Some(mode) = query.mode {
        query_builder.push(" AND mode = ");
        query_builder.push_bind(mode);
        query_builder.push("::event_mode");
    }

    if let Some(entity_name) = query.entity {
        query_builder.push(" AND entity->>'name' ILIKE ");
        query_builder.push_bind(format!("%{}%", entity_name));
    }

    if let Some(entity_id) = query.entity_id {
        query_builder.push(" AND e.id = ");
        query_builder.push_bind(entity_id);
    }

    match query_builder
        .build_query_as::<types::Session>()
        .fetch_all(db_pool)
        .await
    {
        Ok(sessions) => Json(sessions).into_response(),
        Err(e) => {
            eprintln!("Database query failed: {:?}", e);
            axum::http::StatusCode::INTERNAL_SERVER_ERROR.into_response()
        }
    }
}
