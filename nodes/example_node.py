from typing import Any
from griptape_nodes.exe_types.node_types import DataNode
from griptape_nodes.exe_types.core_types import Parameter, ParameterMode, ParameterTypeBuiltin
from griptape_nodes.traits.options import Options
from griptape_nodes.traits.slider import Slider

class ExampleNode(DataNode):
    def __init__(self, name: str, metadata: dict[Any, Any] | None = None) -> None:
        super().__init__(name, metadata)

        # Free text entry parameter
        self.add_parameter(
            Parameter(
                name="free_text",
                tooltip="Enter any text",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY, ParameterMode.OUTPUT},
                ui_options={
                    "display_name": "Free Text",
                    "multiline": True
                }
            )
        )

        # Dropdown parameter
        self.add_parameter(
            Parameter(
                name="dropdown",
                tooltip="Select an option",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY, ParameterMode.OUTPUT},
                traits={Options(choices=["yes", "no", "maybe"])},
                ui_options={
                    "display_name": "Dropdown"
                },
                default_value="yes"
            )
        )

        # Integer slider parameter
        self.add_parameter(
            Parameter(
                name="integer_slider",
                tooltip="Select a value",
                type=ParameterTypeBuiltin.INT.value,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY, ParameterMode.OUTPUT},
                traits={Slider(min_val=1, max_val=10)},
                ui_options={
                    "display_name": "Integer Slider",
                    "step": 1
                },
                default_value=5
            )
        )

        # Output text parameter
        self.add_parameter(
            Parameter(
                name="reversed_text",
                tooltip="Reversed words from free text",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.OUTPUT},
                ui_options={
                    "display_name": "Reversed Text",
                    "multiline": True
                }
            )
        )

        # Random float parameter
        self.add_parameter(
            Parameter(
                name="random_float",
                tooltip="Random float between 0 and integer slider",
                type=ParameterTypeBuiltin.FLOAT.value,
                allowed_modes={ParameterMode.OUTPUT},
                ui_options={
                    "display_name": "Random Float"
                }
            )
        )

    def process(self) -> None:
        # Example processing logic
        free_text = self.get_parameter_value("free_text")
        dropdown = self.get_parameter_value("dropdown")
        integer_slider = self.get_parameter_value("integer_slider")

        # Reverse the words in free_text
        if free_text:
            reversed_words = ' '.join(reversed(free_text.split()))
            self.parameter_output_values["reversed_text"] = reversed_words
        else:
            self.parameter_output_values["reversed_text"] = ""

        # Calculate random float
        import random
        random_float = round(random.uniform(0, integer_slider), 3)
        self.parameter_output_values["random_float"] = random_float

        # For demonstration, just print the values
        print(f"Free Text: {free_text}, Dropdown: {dropdown}, Integer Slider: {integer_slider}, Reversed Text: {self.parameter_output_values['reversed_text']}, Random Float: {random_float}") 