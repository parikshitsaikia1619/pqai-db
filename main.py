"""Server

Attributes:
    app (fastapi.applications.FastAPI): FastAPI instance
    PORT (int): Port number
"""

import os
import uvicorn
import json
import re
from fastapi import FastAPI, Response
import dotenv
import boto3
import botocore

dotenv.load_dotenv()

from core.storage import S3Bucket

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

config = botocore.config.Config(
    read_timeout=400,
    connect_timeout=400,
    retries={"max_attempts": 0}
)
credentials = {
    'aws_access_key_id': AWS_ACCESS_KEY_ID,
    'aws_secret_access_key': AWS_SECRET_ACCESS_KEY
}
botoclient = boto3.client('s3', **credentials, config=config)
bucket_name = os.environ.get("AWS_S3_BUCKET_NAME")
s3_storage = S3Bucket(botoclient, bucket_name)

app = FastAPI()

def get_drawing_prefix(doc_id):
    """Maps document ids to their drawing path prefixes
    For US Patent No. 7,654,321 the drawings are stored as follows:
        07654321-1.tif
        07654321-2.tif
        ...
        ...
    For US patent applications, say, for US20080156487A1, they're stored as:
        US20080156487A1-1.tif
        US20080156487A1-2.tif
        ...
        ...
    This function creates the appropriate key prefix on the basis of whether
    the supplied number is a patent or an application.
    Args:
        doc_id (str): Document identifier (e.g. patent number)
    Returns:
        str: Drawing prefix
    """
    if len(doc_id) > 12:
        return f'images/{doc_id}-'

    num = re.search(r'\d+', doc_id).group(0)
    while len(num) < 8:
        num = '0' + num
    return f'images/{num}-'


@app.get('/patents/{doc_id}')
async def get_doc(doc_id):
    """Return a document's data in JSON format
    """
    doc = s3_storage.get(f"patents/{doc_id}.json")
    return json.loads(doc)

@app.get('/patents/{doc_id}/drawings')
async def list_drawings(doc_id):
    """Return a list of drawings associated with a document, e.g., [1, 2, 3]
    """
    key_prefix = get_drawing_prefix(doc_id)
    keys = s3_storage.ls(key_prefix)
    drawings = [re.search(r'-(\d+)', key).group(1) for key in keys]
    return drawings

@app.get('/patents/{doc_id}/drawings/{drawing_num}')
async def get_drawing(doc_id, drawing_num):
    """Return image data of a particular drawing
    """
    key_prefix = get_drawing_prefix(doc_id)
    key = f'{key_prefix}{drawing_num}.tif'
    print(key)
    tif_data = s3_storage.get(key)
    return Response(content=tif_data, media_type='image/tiff')


if __name__ == "__main__":
    port = int(os.environ["PORT"])
    uvicorn.run(app, host="0.0.0.0", port=port)
