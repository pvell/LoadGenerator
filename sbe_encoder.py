import struct
import xml.etree.ElementTree as ET

def load_schema(schema_file):
    tree = ET.parse(schema_file)
    root = tree.getroot()

    messages = {}

    # Find the XML namespace
    namespace = root.tag.split('}')[0] + '}'

    type_counter = 1

    # Load message definitions
    for message_elem in root.iter(f'{namespace}message'):
        message_id = int(message_elem.attrib["id"])
        message_name = message_elem.attrib["name"]
        fields = {}

        for field_elem in message_elem.iter(f'field'):
            field_id = int(field_elem.attrib["id"])
            field_name = field_elem.attrib["name"]
            field_type = field_elem.attrib.get("type")
            fields[field_id] = {
                "name": field_name,
                "type": field_type
            }

        messages[message_name] = {
            "id": message_id,
            "fields": fields
        }

    # Load type definitions
    for type_elem in root.iter(f'type'):
        type_name = type_elem.attrib["name"]
        type_fields = {}

        for sub_type_elem in type_elem.iter(f'type'):
            sub_type_name = sub_type_elem.attrib["name"]
            sub_type_primitive = sub_type_elem.attrib.get("primitiveType")
            type_fields[sub_type_name] = sub_type_primitive

        if not type_fields:
            type_fields[type_name] = type_elem.text

        messages[type_name] = {
            "id": type_counter,
            "fields": type_fields
        }

        type_counter += 1

    return messages


def encode_message(schema_file, message_name, field_values):
    schema = load_schema(schema_file)
    message = schema.get(message_name)
    if not message:
        raise ValueError(f"Invalid message name '{message_name}'")

    encoded_fields = []
    for field_id, field_data in message['fields'].items():
        field_name = field_data['name']
        field_type = field_data['type']
        field_value = field_values.get(field_name, None)
        encoded_field = encode_field(field_id, field_value, field_type, schema, field_values)
        encoded_fields.append(encoded_field)

    encoded_message = b''.join(encoded_fields)
    return encoded_message


def encode_field(tag, value, field_type, schema, field_values):
    encoded_value = b''

    if field_type == 'int':
        encoded_value = struct.pack('!i', int(value))
    elif field_type == 'uint':
        encoded_value = struct.pack('!I', int(value))
    elif field_type == 'float':
        encoded_value = struct.pack('!f', float(value))
    elif field_type == 'double':
        encoded_value = struct.pack('!d', float(value))
    elif field_type == 'char':
        value = value if value is not None else ''
        encoded_value = struct.pack('!s', value.encode())
    elif field_type == 'boolean':
        encoded_value = struct.pack('!?', bool(value))
    elif field_type.startswith('group'):
        group_fields = field_type.split(':')[1:]
        for group_field in group_fields:
            group_tag, group_value = group_field.split('=')
            encoded_group_field = encode_field(int(group_tag), group_value, field_type, schema, field_values)
            encoded_value += encoded_group_field
    elif field_type.startswith('composite'):
        composite_fields = schema.get(field_type.split(':')[1])
        if not composite_fields:
            raise ValueError(f"Invalid composite field '{field_type}'")
        for sub_field_data in composite_fields['fields'].values():
            sub_field_id = sub_field_data['id']
            sub_field_type = sub_field_data['type']
            sub_field_name = sub_field_data['name']
            sub_field_value = field_values.get(sub_field_name, None)
            encoded_sub_field = encode_field(sub_field_id, sub_field_value, sub_field_type, schema, field_values)
            encoded_value += encoded_sub_field

    return encoded_value


# Example usage
schema_file = 'sbe-schema-options.xml'
message_name = 'NewOrderSingle'
field_values = {
    'ClOrdID': 'CLORD12345',
    'MPID': 'MPID123',
    'Symbol': 'AAPL',
    'SymbolSfx': None,
    'Side': 'BUY',
    'OrderQty': 100,
    'OrdType': 'LIMIT',
    'Price': 99.99,
    'TimeInForce': 'DAY',
    'OrderCapacity': 'AGENCY',
    'CustOrderCapacity': 'RETAIL'
}

encoded_message = encode_message(schema_file, message_name, field_values)
print('Encoded Message:', encoded_message)
