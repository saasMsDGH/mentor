"""Frozen initial schema for new MENTOR PostgreSQL databases.

Revision ID: mentor_pg_0001
This baseline is separate from the incremental OpenTutor migration history.
The vector extension must be provisioned by the database operator first.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

revision = "mentor_pg_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""DO $mentor$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
            RAISE EXCEPTION 'The vector extension must be provisioned before MENTOR migrations';
        END IF;
    END $mentor$""")
    # Frozen schema; keep this revision independent from future ORM changes.
    op.create_table('cognitive_baselines',
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('avg_message_length', sa.Float(), nullable=False),
    sa.Column('avg_word_count', sa.Float(), nullable=False),
    sa.Column('help_seeking_rate', sa.Float(), nullable=False),
    sa.Column('message_count', sa.Integer(), nullable=False),
    sa.Column('session_count', sa.Integer(), nullable=False),
    sa.Column('total_length', sa.Float(), nullable=False),
    sa.Column('total_words', sa.Float(), nullable=False),
    sa.Column('help_count', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('users',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('hashed_password', sa.String(length=255), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('auth_sessions',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('domain', sa.String(length=200), nullable=False),
    sa.Column('session_name', sa.String(length=100), nullable=False),
    sa.Column('auth_type', sa.String(length=30), nullable=False),
    sa.Column('is_valid', sa.Boolean(), nullable=False),
    sa.Column('last_validated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('login_actions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('login_url', sa.Text(), nullable=True),
    sa.Column('check_url', sa.Text(), nullable=True),
    sa.Column('success_selector', sa.String(length=200), nullable=True),
    sa.Column('failure_selector', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_name')
    )
    op.create_index(op.f('ix_auth_sessions_domain'), 'auth_sessions', ['domain'], unique=False)
    op.create_table('courses',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('active_scene', sa.String(length=50), nullable=True),
    sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('integration_credentials',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('integration_name', sa.String(length=50), nullable=False),
    sa.Column('access_token', sa.Text(), nullable=False),
    sa.Column('refresh_token', sa.Text(), nullable=True),
    sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'integration_name', name='uq_user_integration')
    )
    op.create_table('learning_templates',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_builtin', sa.Boolean(), nullable=False),
    sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('scene_id', sa.String(length=50), nullable=True),
    sa.Column('tab_preset', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('workflow', sa.String(length=50), nullable=True),
    sa.Column('target_audience', sa.String(length=100), nullable=True),
    sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('agent_kv',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('namespace', sa.String(length=64), nullable=False),
    sa.Column('key', sa.String(length=256), nullable=False),
    sa.Column('value_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'course_id', 'namespace', 'key', name='uq_agent_kv_user_course_ns_key')
    )
    op.create_index('ix_agent_kv_user_ns', 'agent_kv', ['user_id', 'namespace'], unique=False)
    op.create_table('chat_sessions',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('scene_id', sa.String(length=50), nullable=True),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('channel', sa.String(length=30), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_session_user_course', 'chat_sessions', ['user_id', 'course_id'], unique=False)
    op.create_index('ix_chat_session_user_course_updated', 'chat_sessions', ['user_id', 'course_id', 'updated_at'], unique=False)
    op.create_table('conversation_memories',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('memory_type', sa.String(length=20), nullable=False),
    sa.Column('category', sa.String(length=100), nullable=True),
    sa.Column('embedding', pgvector.sqlalchemy.Vector(1536), nullable=True),
    sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
    sa.Column('importance', sa.Float(), nullable=False),
    sa.Column('access_count', sa.Integer(), nullable=False),
    sa.Column('source_message', sa.Text(), nullable=True),
    sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('dismissal_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_mem_search_vector', 'conversation_memories', ['search_vector'], unique=False, postgresql_using='gin')
    op.create_index('ix_mem_user_course', 'conversation_memories', ['user_id', 'course_id'], unique=False)
    op.create_index('ix_mem_user_type', 'conversation_memories', ['user_id', 'memory_type'], unique=False)
    op.create_table('course_content_tree',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.Column('order_index', sa.Integer(), nullable=False),
    sa.Column('source_file', sa.String(length=500), nullable=True),
    sa.Column('source_type', sa.String(length=20), nullable=False),
    sa.Column('content_category', sa.String(length=50), nullable=True),
    sa.Column('blocks_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
    sa.Column('embedding', pgvector.sqlalchemy.Vector(1536), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['parent_id'], ['course_content_tree.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_content_tree_course_order', 'course_content_tree', ['course_id', 'order_index'], unique=False)
    op.create_index('ix_content_tree_course_parent', 'course_content_tree', ['course_id', 'parent_id'], unique=False)
    op.create_index('ix_content_tree_search_vector', 'course_content_tree', ['search_vector'], unique=False, postgresql_using='gin')
    op.create_table('generated_assets',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('asset_type', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('batch_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('is_archived', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ingestion_jobs',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('source_type', sa.String(length=20), nullable=False),
    sa.Column('original_filename', sa.String(length=500), nullable=True),
    sa.Column('url', sa.Text(), nullable=True),
    sa.Column('mime_type', sa.String(length=100), nullable=True),
    sa.Column('file_path', sa.String(length=1000), nullable=True),
    sa.Column('file_size', sa.Integer(), nullable=True),
    sa.Column('content_hash', sa.String(length=64), nullable=True),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('course_preset', sa.Boolean(), nullable=False),
    sa.Column('content_category', sa.String(length=50), nullable=True),
    sa.Column('classification_method', sa.String(length=20), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('progress_percent', sa.Integer(), nullable=False),
    sa.Column('phase_label', sa.String(length=100), nullable=True),
    sa.Column('embedding_status', sa.String(length=20), nullable=False),
    sa.Column('nodes_created', sa.Integer(), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('dispatched', sa.Boolean(), nullable=False),
    sa.Column('dispatched_to', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('user_corrected_category', sa.String(length=50), nullable=True),
    sa.Column('user_corrected_course', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('extracted_markdown', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ingestion_jobs_content_hash'), 'ingestion_jobs', ['content_hash'], unique=False)
    op.create_table('intervention_outcomes',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('intervention_type', sa.String(length=50), nullable=False),
    sa.Column('block_type', sa.String(length=50), nullable=False),
    sa.Column('signal_source', sa.String(length=50), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('cognitive_load_before', sa.Float(), nullable=True),
    sa.Column('cognitive_load_after', sa.Float(), nullable=True),
    sa.Column('was_effective', sa.Boolean(), nullable=True),
    sa.Column('user_feedback', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_intervention_unresolved', 'intervention_outcomes', ['user_id', 'resolved_at'], unique=False)
    op.create_index('ix_intervention_user_course_time', 'intervention_outcomes', ['user_id', 'course_id', 'created_at'], unique=False)
    op.create_table('mastery_snapshots',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('content_node_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('mastery_score', sa.Float(), nullable=False),
    sa.Column('gap_type', sa.String(length=30), nullable=True),
    sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_mastery_snap_user_course_time', 'mastery_snapshots', ['user_id', 'course_id', 'recorded_at'], unique=False)
    op.create_table('notifications',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=False),
    sa.Column('read', sa.Boolean(), nullable=False),
    sa.Column('batch_key', sa.String(length=200), nullable=True),
    sa.Column('dedup_key', sa.String(length=200), nullable=True),
    sa.Column('priority', sa.String(length=20), nullable=True),
    sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=True),
    sa.Column('sent_via', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('action_url', sa.String(length=500), nullable=True),
    sa.Column('action_label', sa.String(length=100), nullable=True),
    sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('preference_signals',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('signal_type', sa.String(length=20), nullable=False),
    sa.Column('dimension', sa.String(length=50), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('dismissal_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('study_goals',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('objective', sa.Text(), nullable=False),
    sa.Column('success_metric', sa.String(length=200), nullable=True),
    sa.Column('current_milestone', sa.String(length=200), nullable=True),
    sa.Column('next_action', sa.String(length=200), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('confidence', sa.String(length=20), nullable=True),
    sa.Column('target_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_study_goal_user_course_status_created', 'study_goals', ['user_id', 'course_id', 'status', 'created_at'], unique=False)
    op.create_index('ix_study_goal_user_status_target', 'study_goals', ['user_id', 'status', 'target_date'], unique=False)
    op.create_table('study_plans',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('scene_id', sa.String(length=50), nullable=True),
    sa.Column('tasks', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('study_sessions',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('duration_minutes', sa.Integer(), nullable=True),
    sa.Column('messages_sent', sa.Integer(), nullable=False),
    sa.Column('problems_attempted', sa.Integer(), nullable=False),
    sa.Column('problems_correct', sa.Integer(), nullable=False),
    sa.Column('notes_viewed', sa.Integer(), nullable=False),
    sa.Column('signals_extracted', sa.Integer(), nullable=False),
    sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('usage_events',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('agent_name', sa.String(length=64), nullable=True),
    sa.Column('scene', sa.String(length=64), nullable=True),
    sa.Column('model_provider', sa.String(length=64), nullable=False),
    sa.Column('model_name', sa.String(length=128), nullable=False),
    sa.Column('input_tokens', sa.Integer(), nullable=False),
    sa.Column('output_tokens', sa.Integer(), nullable=False),
    sa.Column('estimated_cost_usd', sa.Float(), nullable=False),
    sa.Column('tool_calls', sa.Integer(), nullable=False),
    sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usage_events_created_at'), 'usage_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_usage_events_user_id'), 'usage_events', ['user_id'], unique=False)
    op.create_table('user_preferences',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('scope', sa.String(length=20), nullable=False),
    sa.Column('scene_type', sa.String(length=50), nullable=True),
    sa.Column('dimension', sa.String(length=50), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('dismissal_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_preference_user', 'user_preferences', ['user_id'], unique=False)
    op.create_table('agent_tasks',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('goal_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('task_type', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('source', sa.String(length=30), nullable=False),
    sa.Column('input_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('result_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('max_attempts', sa.Integer(), nullable=False),
    sa.Column('requires_approval', sa.Boolean(), nullable=False),
    sa.Column('task_kind', sa.String(length=30), nullable=False),
    sa.Column('risk_level', sa.String(length=20), nullable=False),
    sa.Column('approval_status', sa.String(length=20), nullable=False),
    sa.Column('approval_reason', sa.Text(), nullable=True),
    sa.Column('approval_action', sa.Text(), nullable=True),
    sa.Column('checkpoint_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('step_results_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('provenance_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cancel_requested_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['goal_id'], ['study_goals.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_task_status_approval_created', 'agent_tasks', ['status', 'requires_approval', 'created_at'], unique=False)
    op.create_index('ix_agent_task_user_course_created', 'agent_tasks', ['user_id', 'course_id', 'created_at'], unique=False)
    op.create_index('ix_agent_task_user_status_created', 'agent_tasks', ['user_id', 'status', 'created_at'], unique=False)
    op.create_table('assignments',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('assignment_type', sa.String(length=50), nullable=True),
    sa.Column('source_ingestion_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_ingestion_id'], ['ingestion_jobs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('chat_message_logs',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_message_session_created', 'chat_message_logs', ['session_id', 'created_at'], unique=False)
    op.create_table('knowledge_nodes',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=True),
    sa.Column('content_node_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['content_node_id'], ['course_content_tree.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('course_id', 'name', name='uq_knowledge_node_course_name')
    )
    op.create_table('learning_progress',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('content_node_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('mastery_score', sa.Float(), nullable=False),
    sa.Column('time_spent_minutes', sa.Integer(), nullable=False),
    sa.Column('review_count', sa.Integer(), nullable=False),
    sa.Column('quiz_attempts', sa.Integer(), nullable=False),
    sa.Column('quiz_correct', sa.Integer(), nullable=False),
    sa.Column('gap_type', sa.String(length=30), nullable=True),
    sa.Column('next_review_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ease_factor', sa.Float(), nullable=False),
    sa.Column('interval_days', sa.Integer(), nullable=False),
    sa.Column('fsrs_difficulty', sa.Float(), nullable=False),
    sa.Column('fsrs_stability', sa.Float(), nullable=False),
    sa.Column('fsrs_reps', sa.Integer(), nullable=False),
    sa.Column('fsrs_lapses', sa.Integer(), nullable=False),
    sa.Column('fsrs_state', sa.String(length=20), nullable=False),
    sa.Column('last_studied_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['content_node_id'], ['course_content_tree.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('practice_problems',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('content_node_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('question_type', sa.String(length=20), nullable=False),
    sa.Column('question', sa.Text(), nullable=False),
    sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('correct_answer', sa.Text(), nullable=True),
    sa.Column('explanation', sa.Text(), nullable=True),
    sa.Column('order_index', sa.Integer(), nullable=False),
    sa.Column('knowledge_points', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('source', sa.String(length=20), nullable=True),
    sa.Column('difficulty_layer', sa.Integer(), nullable=True),
    sa.Column('problem_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('parent_problem_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('is_diagnostic', sa.Boolean(), nullable=False),
    sa.Column('source_batch_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('source_version', sa.Integer(), nullable=False),
    sa.Column('is_archived', sa.Boolean(), nullable=False),
    sa.Column('source_owner', sa.String(length=20), nullable=False),
    sa.Column('locked', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['content_node_id'], ['course_content_tree.id'], ),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['parent_problem_id'], ['practice_problems.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_practice_problem_course', 'practice_problems', ['course_id'], unique=False)
    op.create_table('scrape_sources',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('label', sa.String(length=300), nullable=True),
    sa.Column('source_type', sa.String(length=30), nullable=False),
    sa.Column('requires_auth', sa.Boolean(), nullable=False),
    sa.Column('auth_domain', sa.String(length=200), nullable=True),
    sa.Column('session_name', sa.String(length=100), nullable=True),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('interval_hours', sa.Integer(), nullable=False),
    sa.Column('last_scraped_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_content_hash', sa.String(length=64), nullable=True),
    sa.Column('last_status', sa.String(length=20), nullable=True),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('consecutive_failures', sa.Integer(), nullable=False),
    sa.Column('last_ingestion_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("source_type IN ('generic', 'canvas')", name='ck_scrape_sources_source_type'),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['last_ingestion_id'], ['ingestion_jobs.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('agenda_runs',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('goal_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('trigger', sa.String(length=30), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('top_signal_type', sa.String(length=50), nullable=True),
    sa.Column('signals_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('decision_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('dedup_key', sa.String(length=300), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['goal_id'], ['study_goals.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['task_id'], ['agent_tasks.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agenda_run_dedup', 'agenda_runs', ['user_id', 'dedup_key', 'created_at'], unique=False)
    op.create_index('ix_agenda_run_user_course_created', 'agenda_runs', ['user_id', 'course_id', 'created_at'], unique=False)
    op.create_index('ix_agenda_run_user_created', 'agenda_runs', ['user_id', 'created_at'], unique=False)
    op.create_table('concept_mastery',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('knowledge_node_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('mastery_score', sa.Float(), nullable=False),
    sa.Column('practice_count', sa.Integer(), nullable=False),
    sa.Column('correct_count', sa.Integer(), nullable=False),
    sa.Column('wrong_count', sa.Integer(), nullable=False),
    sa.Column('last_practiced_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('next_review_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('stability_days', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['knowledge_node_id'], ['knowledge_nodes.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'knowledge_node_id', name='uq_concept_mastery_user_node')
    )
    op.create_table('knowledge_edges',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('relation_type', sa.String(length=30), nullable=False),
    sa.Column('weight', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['source_id'], ['knowledge_nodes.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['target_id'], ['knowledge_nodes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_id', 'target_id', 'relation_type', name='uq_knowledge_edge')
    )
    op.create_table('practice_results',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('problem_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_answer', sa.Text(), nullable=False),
    sa.Column('is_correct', sa.Boolean(), nullable=False),
    sa.Column('ai_explanation', sa.Text(), nullable=True),
    sa.Column('error_category', sa.String(length=30), nullable=True),
    sa.Column('difficulty_layer', sa.Integer(), nullable=True),
    sa.Column('answer_time_ms', sa.Integer(), nullable=True),
    sa.Column('answered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['problem_id'], ['practice_problems.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('wrong_answers',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('problem_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_answer', sa.Text(), nullable=False),
    sa.Column('correct_answer', sa.Text(), nullable=True),
    sa.Column('explanation', sa.Text(), nullable=True),
    sa.Column('error_category', sa.String(length=30), nullable=True),
    sa.Column('knowledge_points', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('diagnosis', sa.String(length=30), nullable=True),
    sa.Column('error_detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('review_count', sa.Integer(), nullable=False),
    sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('mastered', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['problem_id'], ['practice_problems.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_wrong_answers_course_mastered', 'wrong_answers', ['course_id', 'mastered'], unique=False)
    op.create_index('ix_wrong_answers_user_course', 'wrong_answers', ['user_id', 'course_id'], unique=False)


    op.create_index('ix_content_tree_embedding_hnsw', 'course_content_tree', ['embedding'],
                    postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.create_index('ix_mem_embedding_hnsw', 'conversation_memories', ['embedding'],
                    postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'})


def downgrade():
    op.drop_index('ix_mem_embedding_hnsw', table_name='conversation_memories')
    op.drop_index('ix_content_tree_embedding_hnsw', table_name='course_content_tree')
    # Frozen schema; keep this revision independent from future ORM changes.
    op.drop_index('ix_wrong_answers_user_course', table_name='wrong_answers')
    op.drop_index('ix_wrong_answers_course_mastered', table_name='wrong_answers')
    op.drop_table('wrong_answers')
    op.drop_table('practice_results')
    op.drop_table('knowledge_edges')
    op.drop_table('concept_mastery')
    op.drop_index('ix_agenda_run_user_created', table_name='agenda_runs')
    op.drop_index('ix_agenda_run_user_course_created', table_name='agenda_runs')
    op.drop_index('ix_agenda_run_dedup', table_name='agenda_runs')
    op.drop_table('agenda_runs')
    op.drop_table('scrape_sources')
    op.drop_index('ix_practice_problem_course', table_name='practice_problems')
    op.drop_table('practice_problems')
    op.drop_table('learning_progress')
    op.drop_table('knowledge_nodes')
    op.drop_index('ix_chat_message_session_created', table_name='chat_message_logs')
    op.drop_table('chat_message_logs')
    op.drop_table('assignments')
    op.drop_index('ix_agent_task_user_status_created', table_name='agent_tasks')
    op.drop_index('ix_agent_task_user_course_created', table_name='agent_tasks')
    op.drop_index('ix_agent_task_status_approval_created', table_name='agent_tasks')
    op.drop_table('agent_tasks')
    op.drop_index('ix_user_preference_user', table_name='user_preferences')
    op.drop_table('user_preferences')
    op.drop_index(op.f('ix_usage_events_user_id'), table_name='usage_events')
    op.drop_index(op.f('ix_usage_events_created_at'), table_name='usage_events')
    op.drop_table('usage_events')
    op.drop_table('study_sessions')
    op.drop_table('study_plans')
    op.drop_index('ix_study_goal_user_status_target', table_name='study_goals')
    op.drop_index('ix_study_goal_user_course_status_created', table_name='study_goals')
    op.drop_table('study_goals')
    op.drop_table('preference_signals')
    op.drop_table('notifications')
    op.drop_index('ix_mastery_snap_user_course_time', table_name='mastery_snapshots')
    op.drop_table('mastery_snapshots')
    op.drop_index('ix_intervention_user_course_time', table_name='intervention_outcomes')
    op.drop_index('ix_intervention_unresolved', table_name='intervention_outcomes')
    op.drop_table('intervention_outcomes')
    op.drop_index(op.f('ix_ingestion_jobs_content_hash'), table_name='ingestion_jobs')
    op.drop_table('ingestion_jobs')
    op.drop_table('generated_assets')
    op.drop_index('ix_content_tree_search_vector', table_name='course_content_tree')
    op.drop_index('ix_content_tree_course_parent', table_name='course_content_tree')
    op.drop_index('ix_content_tree_course_order', table_name='course_content_tree')
    op.drop_table('course_content_tree')
    op.drop_index('ix_mem_user_type', table_name='conversation_memories')
    op.drop_index('ix_mem_user_course', table_name='conversation_memories')
    op.drop_index('ix_mem_search_vector', table_name='conversation_memories')
    op.drop_table('conversation_memories')
    op.drop_index('ix_chat_session_user_course_updated', table_name='chat_sessions')
    op.drop_index('ix_chat_session_user_course', table_name='chat_sessions')
    op.drop_table('chat_sessions')
    op.drop_index('ix_agent_kv_user_ns', table_name='agent_kv')
    op.drop_table('agent_kv')
    op.drop_table('learning_templates')
    op.drop_table('integration_credentials')
    op.drop_table('courses')
    op.drop_index(op.f('ix_auth_sessions_domain'), table_name='auth_sessions')
    op.drop_table('auth_sessions')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_table('cognitive_baselines')
