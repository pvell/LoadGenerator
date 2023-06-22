import xml.etree.ElementTree as ET

def load_schema(schema_file):
    tree = ET.parse(schema_file)
    root = tree.getroot()

    composite_dict = {}
    type_dict = {}

    # Load composite definitions
    for composite_def in root.iter("composite"):
        composite_id = int(composite_def.attrib["id"])
        fields = {}
        for field_def in composite_def.iter("field"):
            field_id = int(field_def.attrib["id"])
            field_name = field_def.attrib["name"]
            fields[field_id] = field_name
        composite_dict[composite_id] = fields

    # Load type definitions
    for type_def in root.iter("type"):
        type_id = int(type_def.attrib["id"])
        type_name = type_def.attrib["name"]
        type_dict[type_id] = type_name

    return composite_dict, type_dict

def encode_message(schema_file, message_name, field_values):
    composite_dict, type_dict = load_schema(schema_file)
    print(composite_dict, type_dict)
    composite_fields = composite_dict.get(message_name)
    if not composite_fields:
        raise ValueError(f"Invalid message name '{message_name}'")

    encoded_fields = []
    for field_id, field_name in composite_fields:
        field_value = field_values.get(field_id, None)
        encoded_field = encode_field(field_id, field_value, type_dict, composite_dict)
        encoded_fields.append(encoded_field)

    encoded_message = "".join(encoded_fields)
    return encoded_message

def encode_field(field_id, field_value, type_dict, composite_dict):
    type_name = type_dict.get(field_id)
    if not type_name:
        raise ValueError(f"Invalid field ID '{field_id}'")

    encoded_value = ""
    if type_name == "string":
        encoded_value = str(field_value) if field_value is not None else ""
    elif type_name == "int":
        encoded_value = str(field_value) if field_value is not None else "0"
    elif type_name == "float":
        encoded_value = str(field_value) if field_value is not None else "0.0"
    elif type_name == "composite":
        composite_fields = composite_dict.get(field_name)
        if not composite_fields:
            raise ValueError(f"Invalid composite field '{field_name}'")
        for sub_field_id, sub_field_name in composite_fields:
            sub_field_value = field_value.get(sub_field_id, None)
            encoded_sub_field = encode_field(sub_field_id, sub_field_value, type_dict, composite_dict)
            encoded_value += encoded_sub_field

    print(f"Encoded field {field_id}: {encoded_value}")
    return encoded_value

# Example usage
schema_file = "sbe-schema-options.xml"
message_name = "NewOrderSingle"
field_values = {
    52: 1623322435000000000,
    11: "CLORD12345",
    21035: "SECURITY123",
    54: "BUY",
    38: 100,
    40: "LIMIT",
    44: 99.99,
    59: "DAY",
    77: "OPEN",
    18: "ADD",
    1815: "MEDIUM",
    21020: 1,
    21021: 2,
    2362: 123,
    21001: "PREVENT",
    21000: 456,
    21005: 789,
    453: [
        {
            448: "PARTY1",
            447: "SRC1",
            452: 1
        },
        {
            448: "PARTY2",
            447: "SRC2",
            452: 2
        }
    ]
}

encoded_message = encode_message(schema_file, message_name, field_values)
print("Encoded Message:", encoded_message)
