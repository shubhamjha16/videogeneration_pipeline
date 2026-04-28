import pytest
import os
import shutil
import sys
from unittest.mock import patch, MagicMock

# Mock fastembed before any imports
sys.modules["fastembed"] = MagicMock()

def test_heal_symlinks(tmp_path):
    from knowledge_vector_store import VectorStore
    # Create a fake model cache with a symlink
    cache_dir = tmp_path / "models"
    blobs_dir = cache_dir / "blobs"
    blobs_dir.mkdir(parents=True)
    
    real_file = blobs_dir / "actual_model.onnx"
    real_file.write_text("model content")
    
    snapshot_dir = cache_dir / "snapshots" / "v1"
    snapshot_dir.mkdir(parents=True)
    
    symlink_file = snapshot_dir / "model_optimized.onnx"
    os.symlink("../../blobs/actual_model.onnx", symlink_file)
    
    vs = VectorStore.get_instance()
    vs._heal_model_symlinks(str(cache_dir))
    
    assert not os.path.islink(symlink_file)
    assert os.path.isfile(symlink_file)
    assert symlink_file.read_text() == "model content"

def test_vector_store_lazy_load():
    from knowledge_vector_store import VectorStore
    import fastembed
    fastembed.TextEmbedding.reset_mock()
    
    vs = VectorStore()
    with patch("os.path.abspath", return_value="/tmp/models"):
        with patch("os.makedirs"):
            with patch.object(vs, "_heal_model_symlinks"):
                model = vs._get_model()
                assert model is not None
                fastembed.TextEmbedding.assert_called_once()
