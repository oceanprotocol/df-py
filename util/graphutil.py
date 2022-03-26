import requests

def submitQuery(query: str, subgraph_url:str) -> str:
    request = requests.post(subgraph_url, '', json={'query': query})
    if request.status_code != 200:
        raise Exception(f"Query failed. Return code is {request.status_code}\n{query}")

    result = request.json()
    
    return result
