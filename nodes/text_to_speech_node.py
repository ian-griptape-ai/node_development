from typing import Any
import openai
from griptape_nodes.exe_types.node_types import DataNode, NodeResolutionState
from griptape_nodes.exe_types.core_types import Parameter, ParameterMode, ParameterTypeBuiltin
from griptape.drivers.text_to_speech.openai import OpenAiTextToSpeechDriver
from griptape.artifacts import AudioArtifact
from griptape_nodes.traits.options import Options
from griptape_nodes.exe_types.node_types import BaseNode

class TextToSpeechNode(DataNode):
    def __init__(self, name: str, metadata: dict[Any, Any] | None = None) -> None:
        super().__init__(name, metadata)
        
        # Input parameter for text
        self.add_parameter(
            Parameter(
                name="text",
                tooltip="Text to convert to speech",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                ui_options={
                    "display_name": "Text",
                    "multiline": True,
                    "is_full_width": False
                }
            )
        )

        # Voice selection parameter
        self.add_parameter(
            Parameter(
                name="voice",
                tooltip="Voice to use for speech generation",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                default_value="alloy",
                traits={Options(choices=[
                    "alloy",
                    "echo",
                    "fable",
                    "onyx",
                    "nova",
                    "shimmer",
                    "ash",
                    "sage",
                    "coral"
                ])},
                ui_options={
                    "display_name": "Voice"
                }
            )
        )

        # Output format parameter
        self.add_parameter(
            Parameter(
                name="format",
                tooltip="Output audio format",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                default_value="mp3",
                traits={Options(choices=[
                    "mp3",
                    "aac",
                    "opus",
                    "flac",
                    "pcm",
                    "wav"
                ])},
                ui_options={
                    "display_name": "Format"
                }
            )
        )

        # Output parameter for the audio data
        self.add_parameter(
            Parameter(
                name="audio_output",
                tooltip="Generated audio data",
                type="AudioArtifact",
                allowed_modes={ParameterMode.OUTPUT},
                ui_options={
                    "display_name": "Audio Output"
                }
            )
        )

        # Status message parameter
        self.add_parameter(
            Parameter(
                name="status_message",
                tooltip="Status messages about the text-to-speech process",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.PROPERTY},
                ui_options={
                    "multiline": True,
                    "hide": True
                }
            )
        )

    def process(self) -> None:
        """Process the text and generate audio."""
        text = self.get_parameter_value("text")
        voice = self.get_parameter_value("voice")
        format = self.get_parameter_value("format")
        
        if not text:
            self.parameter_values["status_message"] = "No text provided"
            return

        try:
            # Get API key from config
            api_key = self.get_config_value("OpenAI", "OPENAI_API_KEY")
            if not api_key:
                self.parameter_values["status_message"] = "OpenAI API key not found in configuration"
                return

            # Initialize the driver
            driver = OpenAiTextToSpeechDriver(
                model="tts-1",
                voice=voice,
                format=format,
                api_key=api_key
            )

            # Generate audio
            audio_artifact = driver.run_text_to_audio(prompts=[text])
            
            # Set the output
            self.parameter_output_values["audio_output"] = audio_artifact
            self.parameter_values["status_message"] = "Audio generated successfully"

        except Exception as e:
            self.parameter_values["status_message"] = f"Error generating audio: {str(e)}"
            raise

    def mark_for_processing(self) -> None:
        """Mark this node as needing to be processed."""
        # Reset the node's state to UNRESOLVED
        self.state = NodeResolutionState.UNRESOLVED
        
        # Clear any existing output values
        for param in self.parameters:
            if ParameterMode.OUTPUT in param.allowed_modes:
                self.parameter_output_values[param.name] = None

    def after_value_set(self, parameter: Parameter, value: Any, modified_parameters_set: set[str]) -> None:
        # If this parameter change requires reprocessing
        if parameter.name in ["text", "voice", "format"]:  # Replace with your relevant parameter names
            self.mark_for_processing()

    def after_incoming_connection(
        self,
        source_node: BaseNode,  # noqa: ARG002
        source_parameter: Parameter,  # noqa: ARG002
        target_parameter: Parameter,
        modified_parameters_set: set[str],  # noqa: ARG002
    ) -> None:
        """Callback after a Connection has been established TO this Node."""
        # Mark for processing when we get a new input connection
        if target_parameter.name in ["text", "voice", "format"]:
            self.mark_for_processing()

    def after_incoming_connection_removed(
        self,
        source_node: BaseNode,  # noqa: ARG002
        source_parameter: Parameter,  # noqa: ARG002
        target_parameter: Parameter,
        modified_parameters_set: set[str],  # noqa: ARG002
    ) -> None:
        """Callback after a Connection TO this Node was REMOVED."""
        # Mark for processing when an input connection is removed
        if target_parameter.name in ["text", "voice", "format"]:
            self.mark_for_processing()
            # Clear the parameter value since the connection was removed
            self.remove_parameter_value(target_parameter.name)

    def validate_before_workflow_run(self) -> list[Exception] | None:
        """Validate the node configuration before running."""
        exceptions = []
        api_key = self.get_config_value("OpenAI", "OPENAI_API_KEY")
        if not api_key:
            exceptions.append(KeyError("OPENAI_API_KEY is not defined in configuration"))
            return exceptions

        try:
            client = openai.OpenAI(api_key=api_key)
            client.models.list()
        except openai.AuthenticationError as e:
            exceptions.append(e)
        return exceptions if exceptions else None 