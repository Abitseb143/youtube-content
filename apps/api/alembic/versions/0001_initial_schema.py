"""initial schema covering all spec tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-28
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("clerk_user_id", sa.String(128), nullable=False),
        sa.Column("credit_balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("clerk_user_id", name="uq_users_clerk_user_id"),
    )

    # channels
    op.create_table(
        "channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("youtube_channel_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("handle", sa.String(64), nullable=True),
        sa.Column("oauth_refresh_token", sa.Text(), nullable=False),
        sa.Column("oauth_access_token", sa.Text(), nullable=True),
        sa.Column("oauth_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_channels_user_id", "channels", ["user_id"])

    # learning_profiles (referenced by content_series)
    op.create_table(
        "learning_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("top_performers_job_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("negative_signal_job_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("aggregate_features_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("last_recomputed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("channel_id", name="uq_learning_profiles_channel_id"),
    )

    # content_series
    op.create_table(
        "content_series",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("niche", sa.String(255), nullable=True),
        sa.Column("target_format", sa.String(16), nullable=False),
        sa.Column("prompt_template", sa.Text(), nullable=False),
        sa.Column("cadence_cron", sa.String(64), nullable=False),
        sa.Column("auto_approve_after_hours", sa.Integer(), nullable=True),
        sa.Column("voice_id", sa.String(64), nullable=False),
        sa.Column("music_mood", sa.String(64), nullable=False),
        sa.Column("style_preset", sa.String(64), nullable=False),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("learning_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("learning_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("target_format in ('short','long')", name="ck_content_series_target_format"),
    )
    op.create_index(
        "ix_content_series_next_run_at_active",
        "content_series", ["next_run_at"],
        postgresql_where=sa.text("paused_at IS NULL"),
    )

    # jobs
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("series_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_series.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("format", sa.String(16), nullable=False),
        sa.Column("credit_cost", sa.Integer(), nullable=False),
        sa.Column("prompt_resolved", sa.Text(), nullable=True),
        sa.Column("script_text", sa.Text(), nullable=True),
        sa.Column("script_metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("scene_plan_json", postgresql.JSONB(), nullable=True),
        sa.Column("final_video_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("final_thumbnail_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_detail", postgresql.JSONB(), nullable=True),
        sa.Column("current_stage_attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("state_changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_jobs_state_state_changed_at", "jobs", ["state", "state_changed_at"])
    op.create_index("ix_jobs_user_id_created_at", "jobs", ["user_id", sa.text("created_at DESC")])

    # assets
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("s3_key", sa.String(512), nullable=False),
        sa.Column("mime", sa.String(64), nullable=False),
        sa.Column("bytes", sa.BigInteger(), nullable=False),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_assets_job_id", "assets", ["job_id"])

    op.create_foreign_key(
        "fk_jobs_final_video_asset_id_assets", "jobs", "assets",
        ["final_video_asset_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_jobs_final_thumbnail_asset_id_assets", "jobs", "assets",
        ["final_thumbnail_asset_id"], ["id"], ondelete="SET NULL",
    )

    # scenes
    op.create_table(
        "scenes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("image_prompt", sa.Text(), nullable=False),
        sa.Column("narration_text", sa.Text(), nullable=False),
        sa.Column("image_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("clip_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("audio_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kling_external_job_id", sa.String(128), nullable=True),
        sa.Column("visual_state", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("audio_state", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("image_attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clip_attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("audio_attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_scenes_job_id_idx", "scenes", ["job_id", "idx"])

    # credit_transactions
    op.create_table(
        "credit_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_credit_transactions_user_id_created_at",
                    "credit_transactions", ["user_id", sa.text("created_at DESC")])
    op.create_index(
        "ix_credit_transactions_stripe_payment_intent_id",
        "credit_transactions", ["stripe_payment_intent_id"],
        unique=True, postgresql_where=sa.text("stripe_payment_intent_id IS NOT NULL"),
    )
    op.create_index(
        "uq_credit_transactions_job_refund",
        "credit_transactions", ["job_id"],
        unique=True, postgresql_where=sa.text("reason = 'job_refund'"),
    )

    # approval_events
    op.create_table(
        "approval_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # published_videos
    op.create_table(
        "published_videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("youtube_video_id", sa.String(32), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_analytics_pull_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_analytics_pull_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("job_id", name="uq_published_videos_job_id"),
        sa.UniqueConstraint("youtube_video_id", name="uq_published_videos_youtube_video_id"),
    )
    op.create_index(
        "ix_published_videos_next_analytics_pull_at",
        "published_videos", ["next_analytics_pull_at"],
        postgresql_where=sa.text("next_analytics_pull_at IS NOT NULL"),
    )

    # analytics_snapshots
    op.create_table(
        "analytics_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("published_video_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("published_videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pulled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("views", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("watch_time_minutes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("avg_view_duration_s", sa.Float(), nullable=True),
        sa.Column("ctr_pct", sa.Float(), nullable=True),
        sa.Column("likes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("comments", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("subs_gained", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.create_index("ix_analytics_snapshots_published_video_id_pulled_at",
                    "analytics_snapshots", ["published_video_id", "pulled_at"])

    # unit_costs
    op.create_table(
        "unit_costs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("units", sa.Float(), nullable=False),
        sa.Column("usd_cost", sa.Numeric(10, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # job_events
    op.create_table(
        "job_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_state", sa.String(32), nullable=True),
        sa.Column("to_state", sa.String(32), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("worker_id", sa.String(64), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_detail", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_job_events_job_id_at", "job_events", ["job_id", "at"])

    # credit_packs (config table)
    op.create_table(
        "credit_packs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("price_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("stripe_price_id", sa.String(128), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # video_pricing (config table)
    op.create_table(
        "video_pricing",
        sa.Column("format", sa.String(16), primary_key=True),
        sa.Column("credits", sa.Integer(), nullable=False),
    )

    # promo_codes
    op.create_table(
        "promo_codes",
        sa.Column("code", sa.String(64), primary_key=True),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("single_use", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "promo_redemptions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("code", sa.String(64), sa.ForeignKey("promo_codes.code", ondelete="CASCADE"), primary_key=True),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("promo_redemptions")
    op.drop_table("promo_codes")
    op.drop_table("video_pricing")
    op.drop_table("credit_packs")
    op.drop_index("ix_job_events_job_id_at", table_name="job_events")
    op.drop_table("job_events")
    op.drop_table("unit_costs")
    op.drop_index("ix_analytics_snapshots_published_video_id_pulled_at", table_name="analytics_snapshots")
    op.drop_table("analytics_snapshots")
    op.drop_index("ix_published_videos_next_analytics_pull_at", table_name="published_videos")
    op.drop_table("published_videos")
    op.drop_table("approval_events")
    op.drop_index("uq_credit_transactions_job_refund", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_stripe_payment_intent_id", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_user_id_created_at", table_name="credit_transactions")
    op.drop_table("credit_transactions")
    op.drop_index("ix_scenes_job_id_idx", table_name="scenes")
    op.drop_table("scenes")
    op.drop_constraint("fk_jobs_final_thumbnail_asset_id_assets", "jobs", type_="foreignkey")
    op.drop_constraint("fk_jobs_final_video_asset_id_assets", "jobs", type_="foreignkey")
    op.drop_index("ix_assets_job_id", table_name="assets")
    op.drop_table("assets")
    op.drop_index("ix_jobs_user_id_created_at", table_name="jobs")
    op.drop_index("ix_jobs_state_state_changed_at", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_content_series_next_run_at_active", table_name="content_series")
    op.drop_table("content_series")
    op.drop_table("learning_profiles")
    op.drop_index("ix_channels_user_id", table_name="channels")
    op.drop_table("channels")
    op.drop_table("users")
