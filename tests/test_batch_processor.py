"""Tests for batch_processor module."""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from assistant_skills_lib.batch_processor import (
    BatchProgress,
    BatchConfig,
    CheckpointManager,
    BatchProcessor,
    generate_operation_id,
    get_recommended_batch_size,
    list_pending_checkpoints,
)


class TestBatchProgress:
    """Tests for BatchProgress dataclass and properties."""

    def test_is_complete_true(self):
        """Test is_complete returns True when processed >= total."""
        progress = BatchProgress(total_items=10, processed_items=10)
        assert progress.is_complete is True

    def test_is_complete_false(self):
        """Test is_complete returns False when processing incomplete."""
        progress = BatchProgress(total_items=10, processed_items=5)
        assert progress.is_complete is False

    def test_is_complete_over_processed(self):
        """Test is_complete returns True when processed exceeds total."""
        progress = BatchProgress(total_items=10, processed_items=15)
        assert progress.is_complete is True

    def test_percent_complete_zero_total(self):
        """Test percent_complete returns 100% when total_items is 0."""
        progress = BatchProgress(total_items=0, processed_items=0)
        assert progress.percent_complete == 100.0

    def test_percent_complete_partial(self):
        """Test percent_complete calculation for partial progress."""
        progress = BatchProgress(total_items=100, processed_items=25)
        assert progress.percent_complete == 25.0

    def test_percent_complete_full(self):
        """Test percent_complete returns 100% when complete."""
        progress = BatchProgress(total_items=50, processed_items=50)
        assert progress.percent_complete == 100.0

    def test_skipped_items_none(self):
        """Test skipped_items when no items skipped."""
        progress = BatchProgress(
            processed_items=10, successful_items=7, failed_items=3
        )
        assert progress.skipped_items == 0

    def test_skipped_items_some(self):
        """Test skipped_items calculation."""
        progress = BatchProgress(
            processed_items=10, successful_items=5, failed_items=3
        )
        assert progress.skipped_items == 2


class TestBatchConfig:
    """Tests for BatchConfig dataclass and validation."""

    def test_default_values(self):
        """Test default configuration values."""
        config = BatchConfig()
        assert config.batch_size == 50
        assert config.delay_between_batches == 1.0
        assert config.delay_between_items == 0.1
        assert config.max_items == 10000
        assert config.enable_checkpoints is True

    def test_batch_size_clamp_min(self):
        """Test batch_size is clamped to minimum 1."""
        config = BatchConfig(batch_size=0)
        assert config.batch_size == 1

        config = BatchConfig(batch_size=-5)
        assert config.batch_size == 1

    def test_batch_size_clamp_max(self):
        """Test batch_size is clamped to maximum 500."""
        config = BatchConfig(batch_size=1000)
        assert config.batch_size == 500

    def test_delay_between_batches_clamp(self):
        """Test delay_between_batches is clamped to valid range."""
        config = BatchConfig(delay_between_batches=-1.0)
        assert config.delay_between_batches == 0.0

        config = BatchConfig(delay_between_batches=100.0)
        assert config.delay_between_batches == 60.0

    def test_delay_between_items_clamp(self):
        """Test delay_between_items is clamped to valid range."""
        config = BatchConfig(delay_between_items=-1.0)
        assert config.delay_between_items == 0.0

        config = BatchConfig(delay_between_items=20.0)
        assert config.delay_between_items == 10.0

    def test_default_checkpoint_dir(self):
        """Test default checkpoint directory is set."""
        config = BatchConfig()
        assert config.checkpoint_dir is not None
        assert ".assistant-skills" in config.checkpoint_dir
        assert "checkpoints" in config.checkpoint_dir


class TestCheckpointManager:
    """Tests for CheckpointManager class."""

    def test_init_creates_directory(self, tmp_path):
        """Test initialization creates checkpoint directory."""
        checkpoint_dir = tmp_path / "checkpoints"
        assert not checkpoint_dir.exists()

        mgr = CheckpointManager(str(checkpoint_dir), "test-op")

        assert checkpoint_dir.exists()
        assert mgr.operation_id == "test-op"

    def test_exists_false(self, tmp_path):
        """Test exists returns False when no checkpoint."""
        mgr = CheckpointManager(str(tmp_path), "test-op")
        assert mgr.exists() is False

    def test_exists_true(self, tmp_path):
        """Test exists returns True after save."""
        mgr = CheckpointManager(str(tmp_path), "test-op")
        progress = BatchProgress(total_items=10)
        mgr.save(progress)
        assert mgr.exists() is True

    def test_save_creates_file(self, tmp_path):
        """Test save creates checkpoint file."""
        mgr = CheckpointManager(str(tmp_path), "test-op")
        progress = BatchProgress(total_items=10, processed_items=5)

        mgr.save(progress)

        checkpoint_file = tmp_path / "test-op.checkpoint.json"
        assert checkpoint_file.exists()

    def test_save_updates_timestamp(self, tmp_path):
        """Test save updates updated_at timestamp."""
        mgr = CheckpointManager(str(tmp_path), "test-op")
        progress = BatchProgress(total_items=10)
        assert progress.updated_at == ""

        mgr.save(progress)

        assert progress.updated_at != ""
        # Verify it's a valid ISO format
        datetime.fromisoformat(progress.updated_at)

    def test_load_returns_progress(self, tmp_path):
        """Test load returns saved progress."""
        mgr = CheckpointManager(str(tmp_path), "test-op")
        progress = BatchProgress(
            total_items=100,
            processed_items=50,
            successful_items=45,
            failed_items=5,
        )
        mgr.save(progress)

        loaded = mgr.load()

        assert loaded is not None
        assert loaded.total_items == 100
        assert loaded.processed_items == 50
        assert loaded.successful_items == 45
        assert loaded.failed_items == 5

    def test_load_returns_none_when_missing(self, tmp_path):
        """Test load returns None when no checkpoint file."""
        mgr = CheckpointManager(str(tmp_path), "nonexistent-op")
        assert mgr.load() is None

    def test_load_returns_none_on_invalid_json(self, tmp_path):
        """Test load returns None for invalid JSON."""
        mgr = CheckpointManager(str(tmp_path), "test-op")
        checkpoint_file = tmp_path / "test-op.checkpoint.json"
        checkpoint_file.write_text("invalid json {{{")

        assert mgr.load() is None

    def test_clear_removes_file(self, tmp_path):
        """Test clear removes checkpoint file."""
        mgr = CheckpointManager(str(tmp_path), "test-op")
        progress = BatchProgress(total_items=10)
        mgr.save(progress)
        assert mgr.exists() is True

        mgr.clear()

        assert mgr.exists() is False

    def test_clear_no_error_when_missing(self, tmp_path):
        """Test clear does not raise error when file missing."""
        mgr = CheckpointManager(str(tmp_path), "test-op")
        assert mgr.exists() is False
        mgr.clear()  # Should not raise


class TestGenerateOperationId:
    """Tests for generate_operation_id function."""

    def test_format(self):
        """Test operation ID format."""
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        op_id = generate_operation_id("bulk-update", timestamp)

        assert op_id == "bulk-update-20240115-103045"

    def test_uses_current_time_by_default(self):
        """Test that current time is used when not specified."""
        op_id = generate_operation_id("test-op")

        # Should contain operation type prefix
        assert op_id.startswith("test-op-")
        # Should have timestamp portion
        parts = op_id.split("-")
        assert len(parts) >= 3


class TestGetRecommendedBatchSize:
    """Tests for get_recommended_batch_size function."""

    def test_simple_operation(self):
        """Test batch size for simple operations."""
        size = get_recommended_batch_size(100, "simple")
        assert size == 100

    def test_complex_operation(self):
        """Test batch size for complex operations."""
        size = get_recommended_batch_size(100, "complex")
        assert size == 50

    def test_create_operation(self):
        """Test batch size for create operations."""
        size = get_recommended_batch_size(100, "create")
        assert size == 25

    def test_delete_operation(self):
        """Test batch size for delete operations."""
        size = get_recommended_batch_size(100, "delete")
        assert size == 50

    def test_unknown_operation_type(self):
        """Test unknown operation type uses default."""
        size = get_recommended_batch_size(100, "unknown")
        assert size == 50

    def test_large_item_count_reduces_size(self):
        """Test that large item counts reduce batch size."""
        # Over 5000 items -> half size
        size = get_recommended_batch_size(6000, "simple")
        assert size == 50  # 100 / 2

    def test_medium_item_count_reduces_size(self):
        """Test that medium item counts reduce batch size."""
        # Over 1000 items -> 3/4 size
        size = get_recommended_batch_size(1500, "simple")
        assert size == 75  # 100 * 3/4

    def test_minimum_batch_size(self):
        """Test batch size doesn't go below 25."""
        # create (25) with large items -> 25/2 = 12, but min is 25
        size = get_recommended_batch_size(10000, "create")
        assert size == 25


class TestListPendingCheckpoints:
    """Tests for list_pending_checkpoints function."""

    def test_empty_when_no_dir(self, tmp_path):
        """Test returns empty list when directory doesn't exist."""
        nonexistent = tmp_path / "nonexistent"
        result = list_pending_checkpoints(str(nonexistent))
        assert result == []

    def test_empty_when_no_checkpoints(self, tmp_path):
        """Test returns empty list when no checkpoint files."""
        result = list_pending_checkpoints(str(tmp_path))
        assert result == []

    def test_finds_pending_checkpoints(self, tmp_path):
        """Test finds pending (incomplete) checkpoints."""
        # Create a pending checkpoint
        progress = {
            "total_items": 100,
            "processed_items": 50,
            "successful_items": 50,
            "failed_items": 0,
            "current_batch": 1,
            "total_batches": 2,
            "started_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:01:00",
            "errors": {},
            "processed_keys": [],
        }
        checkpoint_file = tmp_path / "test-op.checkpoint.json"
        checkpoint_file.write_text(json.dumps(progress))

        result = list_pending_checkpoints(str(tmp_path))

        assert len(result) == 1
        assert result[0]["operation_id"] == "test-op"
        assert result[0]["progress"] == 50.0
        assert result[0]["processed"] == 50
        assert result[0]["total"] == 100

    def test_ignores_complete_checkpoints(self, tmp_path):
        """Test ignores completed checkpoints."""
        # Create a complete checkpoint
        progress = {
            "total_items": 100,
            "processed_items": 100,
            "successful_items": 100,
            "failed_items": 0,
            "current_batch": 2,
            "total_batches": 2,
            "started_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:01:00",
            "errors": {},
            "processed_keys": [],
        }
        checkpoint_file = tmp_path / "complete-op.checkpoint.json"
        checkpoint_file.write_text(json.dumps(progress))

        result = list_pending_checkpoints(str(tmp_path))

        assert len(result) == 0

    def test_ignores_invalid_json(self, tmp_path):
        """Test ignores files with invalid JSON."""
        checkpoint_file = tmp_path / "invalid.checkpoint.json"
        checkpoint_file.write_text("not valid json")

        result = list_pending_checkpoints(str(tmp_path))

        assert len(result) == 0

    def test_sorted_by_updated_at_descending(self, tmp_path):
        """Test results are sorted by updated_at in descending order."""
        # Create two pending checkpoints with different timestamps
        old_progress = {
            "total_items": 100,
            "processed_items": 25,
            "successful_items": 25,
            "failed_items": 0,
            "current_batch": 1,
            "total_batches": 4,
            "started_at": "2024-01-15T09:00:00",
            "updated_at": "2024-01-15T09:01:00",
            "errors": {},
            "processed_keys": [],
        }
        new_progress = {
            "total_items": 100,
            "processed_items": 75,
            "successful_items": 75,
            "failed_items": 0,
            "current_batch": 3,
            "total_batches": 4,
            "started_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:30:00",
            "errors": {},
            "processed_keys": [],
        }

        (tmp_path / "old-op.checkpoint.json").write_text(json.dumps(old_progress))
        (tmp_path / "new-op.checkpoint.json").write_text(json.dumps(new_progress))

        result = list_pending_checkpoints(str(tmp_path))

        assert len(result) == 2
        # Newer should be first
        assert result[0]["operation_id"] == "new-op"
        assert result[1]["operation_id"] == "old-op"


class TestBatchProcessor:
    """Tests for BatchProcessor class."""

    def test_process_all_items(self, tmp_path):
        """Test processing all items successfully."""
        items = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        processed = []

        def process_item(item):
            processed.append(item["id"])
            return True

        config = BatchConfig(
            batch_size=10,
            delay_between_batches=0,
            delay_between_items=0,
            enable_checkpoints=False,
        )
        processor = BatchProcessor(config=config, process_item=process_item)
        result = processor.process(items, get_key=lambda x: x["id"])

        assert result.total_items == 3
        assert result.processed_items == 3
        assert result.successful_items == 3
        assert result.failed_items == 0
        assert processed == ["1", "2", "3"]

    def test_dry_run_does_not_process(self, tmp_path):
        """Test dry run does not actually process items."""
        items = [{"id": "1"}, {"id": "2"}]
        processed = []

        def process_item(item):
            processed.append(item["id"])
            return True

        config = BatchConfig(enable_checkpoints=False)
        processor = BatchProcessor(config=config, process_item=process_item)
        result = processor.process(items, get_key=lambda x: x["id"], dry_run=True)

        assert result.total_items == 2
        assert len(processed) == 0

    def test_handles_processing_failure(self, tmp_path):
        """Test handling of items that fail processing."""
        items = [{"id": "1"}, {"id": "2"}, {"id": "3"}]

        def process_item(item):
            return item["id"] != "2"  # Item 2 fails

        config = BatchConfig(
            delay_between_batches=0,
            delay_between_items=0,
            enable_checkpoints=False,
        )
        processor = BatchProcessor(config=config, process_item=process_item)
        result = processor.process(items, get_key=lambda x: x["id"])

        assert result.successful_items == 2
        assert result.failed_items == 1
        assert "2" in result.errors

    def test_handles_processing_exception(self, tmp_path):
        """Test handling of exceptions during processing."""
        items = [{"id": "1"}, {"id": "2"}]

        def process_item(item):
            if item["id"] == "2":
                raise ValueError("Test error")
            return True

        config = BatchConfig(
            delay_between_batches=0,
            delay_between_items=0,
            enable_checkpoints=False,
        )
        processor = BatchProcessor(config=config, process_item=process_item)
        result = processor.process(items, get_key=lambda x: x["id"])

        assert result.successful_items == 1
        assert result.failed_items == 1
        assert "Test error" in result.errors["2"]

    def test_respects_max_items(self, tmp_path):
        """Test max_items limit is respected."""
        items = [{"id": str(i)} for i in range(100)]

        config = BatchConfig(
            max_items=10,
            delay_between_batches=0,
            delay_between_items=0,
            enable_checkpoints=False,
        )
        processor = BatchProcessor(config=config, process_item=lambda x: True)
        result = processor.process(items, get_key=lambda x: x["id"])

        assert result.total_items == 10
