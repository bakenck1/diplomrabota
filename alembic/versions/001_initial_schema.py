"""Initial schema for Voice Assistant Pipeline

Revision ID: 001
Revises: 
Create Date: 2024-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="senior"),
        sa.Column("language", sa.String(5), nullable=False, server_default="ru"),
        sa.Column("stt_provider", sa.String(20), nullable=False, server_default="openai"),
        sa.Column("tts_provider", sa.String(20), nullable=False, server_default="openai"),
        sa.Column("is_test_user", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role IN ('senior', 'admin')", name="check_user_role"),
        sa.CheckConstraint("language IN ('ru', 'kk')", name="check_user_language"),
        sa.CheckConstraint("stt_provider IN ('openai', 'google')", name="check_stt_provider"),
        sa.CheckConstraint("tts_provider IN ('openai', 'google')", name="check_tts_provider"),
    )

    # Conversations table
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stt_provider_used", sa.String(20), nullable=False),
        sa.Column("tts_provider_used", sa.String(20), nullable=False),
        sa.Column("device_info", postgresql.JSONB(), nullable=True),
    )
    op.create_index("idx_conversations_user_id", "conversations", ["user_id"])
    op.create_index("idx_conversations_started_at", "conversations", ["started_at"])

    # Turns table
    op.create_table(
        "turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("audio_input_url", sa.String(500), nullable=True),
        sa.Column("audio_input_duration_ms", sa.Integer(), nullable=True),
        sa.Column("raw_transcript", sa.Text(), nullable=True),
        sa.Column("normalized_transcript", sa.Text(), nullable=True),
        sa.Column("transcript_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("stt_latency_ms", sa.Integer(), nullable=True),
        sa.Column("stt_words", postgresql.JSONB(), nullable=True),
        sa.Column("user_confirmed", sa.Boolean(), nullable=True),
        sa.Column("user_correction", sa.Text(), nullable=True),
        sa.Column("llm_prompt_summary", sa.Text(), nullable=True),
        sa.Column("assistant_text", sa.Text(), nullable=True),
        sa.Column("llm_latency_ms", sa.Integer(), nullable=True),
        sa.Column("audio_output_url", sa.String(500), nullable=True),
        sa.Column("audio_output_duration_ms", sa.Integer(), nullable=True),
        sa.Column("tts_latency_ms", sa.Integer(), nullable=True),
        sa.Column("needs_review", sa.Boolean(), server_default="false"),
        sa.Column("low_confidence", sa.Boolean(), server_default="false"),
        sa.UniqueConstraint("conversation_id", "turn_number", name="uq_turn_number"),
    )
    op.create_index("idx_turns_conversation_id", "turns", ["conversation_id"])
    op.create_index(
        "idx_turns_low_confidence",
        "turns",
        ["low_confidence"],
        postgresql_where=sa.text("low_confidence = true"),
    )

    # Unknown Terms table
    op.create_table(
        "unknown_terms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("language", sa.String(5), nullable=False),
        sa.Column("heard_variant", sa.String(255), nullable=False),
        sa.Column("correct_form", sa.String(255), nullable=False),
        sa.Column("context_examples", postgresql.JSONB(), server_default="[]"),
        sa.Column("provider_where_seen", sa.String(20), nullable=True),
        sa.Column("occurrence_count", sa.Integer(), server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.CheckConstraint("language IN ('ru', 'kk')", name="check_term_language"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="check_term_status"),
        sa.UniqueConstraint("language", "heard_variant", name="uq_language_heard_variant"),
    )
    op.create_index("idx_unknown_terms_status", "unknown_terms", ["status"])
    op.create_index("idx_unknown_terms_heard", "unknown_terms", ["heard_variant"])

    # STT Evaluations table
    op.create_table(
        "stt_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("turn_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("turns.id"), nullable=False),
        sa.Column("ground_truth_text", sa.Text(), nullable=False),
        sa.Column("labeled_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("label_source", sa.String(20), nullable=False),
        sa.Column("wer", sa.Numeric(5, 4), nullable=True),
        sa.Column("cer", sa.Numeric(5, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("label_source IN ('user_confirm', 'admin_review')", name="check_label_source"),
    )

    # Audit Logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("idx_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("stt_evaluations")
    op.drop_table("unknown_terms")
    op.drop_table("turns")
    op.drop_table("conversations")
    op.drop_table("users")
