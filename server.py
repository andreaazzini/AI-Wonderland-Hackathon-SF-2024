from flask import Flask, request, jsonify
import utils 
import requests
import tempfile
import os 
from v7_go import Client
import subprocess
import uuid
import json

app = Flask(__name__)


OUTPUT_DIR = "/tmp/"
client = Client(api_key=API_KEY, base_url="https://go.v7labs.com")


def find_entity(workspace_id, project_id, entity_id):
    workspace = [
            workspace
            for workspace in client.workspaces()
            if workspace.id == workspace_id
            ][0]
    project = [
        project
        for project in workspace.projects()
        if project.id == project_id
    ][0]

    for entity in project.entities():
        if entity.id == entity_id:
            return entity
    return None

def get_signed_url(workspace_id, project_id, entity_id):
    headers = { "X-API-KEY": API_KEY }
    response = requests.get(f"https://go.v7labs.com/api/workspaces/{workspace_id}/projects/{project_id}/entities/{entity_id}", headers=headers)
    data = response.json()
    return data["fields"]["form"]["manual_value"]["value"]

def fill_out_pdf(input_pdf, output_pdf):
    utils.extract_form_data_and_options(input_pdf)

@app.route('/trigger', methods=['POST'])
def trigger():
    # Assuming you want to log or work with the incoming JSON
    data = request.get_json()

    entity_id = data["entity"]["id"]
    project_id = data["entity"]["project_id"]

    signed_url = get_signed_url(WORKSPACE_ID, project_id, entity_id)
    response = requests.get(signed_url)
    if response.status_code != 200:
        print("failed to download file", response.text)
        return
    
    temp_dir = OUTPUT_DIR
    id = str(uuid.uuid4())
    filename = f"downloaded_{id}.pdf"
    file_path = os.path.join(temp_dir, filename)

    filled_file_path = os.path.join(temp_dir, f"filled_{id}.pdf")

    with open(file_path, 'wb') as file:
        file.write(response.content)

    form_fields, options_dict = utils.extract_form_data_and_options(file_path)
    
    filled_fields = json.loads(data["entity"]["fields"]["final-json-output"]["data"]["value"])
    utils.fill_pdf(file_path, filled_file_path, filled_fields, options_dict)
    
    # show on computer
    subprocess.run(['open', filled_file_path], check=True)

    return jsonify({"message": "Received"}), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port="5001")