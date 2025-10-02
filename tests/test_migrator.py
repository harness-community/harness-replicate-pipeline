"""
Comprehensive unit tests for HarnessReplicator

Tests replication functionality with proper mocking and AAA methodology.
"""

from unittest.mock import Mock, patch
from src.replicator import HarnessReplicator


class TestHarnessReplicator:
    """Test suite for HarnessReplicator"""

    def setup_method(self):
        """Setup test fixtures before each test method"""
        self.config = {
            "source": {
                "base_url": "https://app.harness.io",
                "api_key": "source-key",
                "org": "source-org",
                "project": "source-project"
            },
            "destination": {
                "base_url": "https://app3.harness.io",
                "api_key": "dest-key",
                "org": "dest-org",
                "project": "dest-project"
            },
            "options": {
                "skip_input_sets": False,
                "skip_triggers": False,
                "skip_templates": False,
                "update_existing": False
            },
            "pipelines": [
                {"identifier": "pipeline1", "name": "Pipeline 1"}
            ]
        }

    def test_init_sets_correct_attributes(self):
        """Test that initialization sets correct attributes"""
        # Arrange & Act
        with patch('src.replicator.HarnessAPIClient') as mock_client_class:
            with patch('src.replicator.PrerequisiteHandler') as mock_prereq:
                with patch('src.replicator.PipelineHandler') as mock_pipeline:
                    with patch('src.replicator.TemplateHandler') as mock_template:
                        with patch('src.replicator.InputSetHandler') as mock_inputset:
                            with patch('src.replicator.TriggerHandler') as mock_trigger:
                                replicator = HarnessReplicator(self.config)

        # Assert
        assert replicator.source_org == "source-org"
        assert replicator.source_project == "source-project"
        assert replicator.dest_org == "dest-org"
        assert replicator.dest_project == "dest-project"
        assert replicator.config == self.config
        
        # Verify API clients were created
        assert mock_client_class.call_count == 2
        
        # Verify handlers were created
        mock_prereq.assert_called_once()
        mock_pipeline.assert_called_once()
        mock_template.assert_called_once()
        mock_inputset.assert_called_once()
        mock_trigger.assert_called_once()

    def test_run_replication_success(self):
        """Test successful replication run"""
        # Arrange
        with patch('src.replicator.HarnessAPIClient'):
            with patch('src.replicator.PrerequisiteHandler') as mock_prereq_class:
                with patch('src.replicator.PipelineHandler') as mock_pipeline_class:
                    with patch('src.replicator.TemplateHandler'):
                        with patch('src.replicator.InputSetHandler'):
                            with patch('src.replicator.TriggerHandler'):
                                # Setup mocks
                                mock_prereq = Mock()
                                mock_prereq.verify_prerequisites.return_value = True
                                mock_prereq_class.return_value = mock_prereq
                                
                                mock_pipeline = Mock()
                                mock_pipeline.replicate_pipelines.return_value = True
                                mock_pipeline_class.return_value = mock_pipeline
                                
                                replicator = HarnessReplicator(self.config)

        # Act
        with patch.object(replicator, 'print_summary') as mock_print_summary:
            result = replicator.run_replication()

        # Assert
        assert result is True
        mock_prereq.verify_prerequisites.assert_called_once()
        mock_pipeline.replicate_pipelines.assert_called_once()
        mock_print_summary.assert_called_once()

    def test_run_replication_prerequisites_fail(self):
        """Test replication fails when prerequisites fail"""
        # Arrange
        with patch('src.replicator.HarnessAPIClient'):
            with patch('src.replicator.PrerequisiteHandler') as mock_prereq_class:
                with patch('src.replicator.PipelineHandler'):
                    with patch('src.replicator.TemplateHandler'):
                        with patch('src.replicator.InputSetHandler'):
                            with patch('src.replicator.TriggerHandler'):
                                # Setup mocks
                                mock_prereq = Mock()
                                mock_prereq.verify_prerequisites.return_value = False
                                mock_prereq_class.return_value = mock_prereq
                                
                                replicator = HarnessReplicator(self.config)

        # Act
        result = replicator.run_replication()

        # Assert
        assert result is False
        mock_prereq.verify_prerequisites.assert_called_once()

    def test_run_replication_pipelines_fail(self):
        """Test replication fails when pipeline replication fails"""
        # Arrange
        with patch('src.replicator.HarnessAPIClient'):
            with patch('src.replicator.PrerequisiteHandler') as mock_prereq_class:
                with patch('src.replicator.PipelineHandler') as mock_pipeline_class:
                    with patch('src.replicator.TemplateHandler'):
                        with patch('src.replicator.InputSetHandler'):
                            with patch('src.replicator.TriggerHandler'):
                                # Setup mocks
                                mock_prereq = Mock()
                                mock_prereq.verify_prerequisites.return_value = True
                                mock_prereq_class.return_value = mock_prereq
                                
                                mock_pipeline = Mock()
                                mock_pipeline.replicate_pipelines.return_value = False
                                mock_pipeline_class.return_value = mock_pipeline
                                
                                replicator = HarnessReplicator(self.config)

        # Act
        result = replicator.run_replication()

        # Assert
        assert result is False
        mock_prereq.verify_prerequisites.assert_called_once()
        mock_pipeline.replicate_pipelines.assert_called_once()

    def test_print_summary(self):
        """Test print_summary uses output orchestrator"""
        # Arrange
        with patch('src.replicator.HarnessAPIClient'):
            with patch('src.replicator.PrerequisiteHandler'):
                with patch('src.replicator.PipelineHandler'):
                    with patch('src.replicator.TemplateHandler'):
                        with patch('src.replicator.InputSetHandler'):
                            with patch('src.replicator.TriggerHandler'):
                                replicator = HarnessReplicator(self.config)

        # Act
        with patch('src.output_orchestrator.get_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            replicator.print_summary()

        # Assert
        mock_get_orchestrator.assert_called_once()
        mock_orchestrator.output_summary.assert_called_once_with(replicator.replication_stats)
