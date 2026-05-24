import xml.etree.ElementTree as ET
import base64


def parse_aadhaar_xml(xml_path):

    tree = ET.parse(xml_path)
    root = tree.getroot()

    uid_data = root.find("UidData")

    poi = uid_data.find("Poi")
    poa = uid_data.find("Poa")

    photo = uid_data.find("Pht").text

    data = {}

    # Extract referenceId
    reference_id = root.attrib.get("referenceId")
    
    data["reference_id"] = reference_id

    # Extract Aadhaar last 4 digits (first 4 digits)
    last4 = reference_id[:4]

    data["masked_aadhaar"] = f"XXXX XXXX {last4}"

    data["name"] = poi.attrib.get("name")
    data["dob"] = poi.attrib.get("dob")
    data["gender"] = poi.attrib.get("gender")

    data["address"] = poa.attrib.get("street")
    data["district"] = poa.attrib.get("dist")
    data["state"] = poa.attrib.get("state")
    data["pincode"] = poa.attrib.get("pc")

    data["photo"] = base64.b64decode(photo)

    return data


