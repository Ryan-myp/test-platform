"""GraphQL router"""
from fastapi import APIRouter
from graphql import graphql_sync
from app.graphql.schema import schema

router = APIRouter(prefix="/api/graphql", tags=["GraphQL"])


@router.post("/")
async def graphql_endpoint(request: dict):
    """GraphQL 端点"""
    result = graphql_sync(schema, request.get("query"), variable_values=request.get("variables"))
    
    response = {
        "data": result.data
    }
    if result.errors:
        response["errors"] = [
            {"message": str(e)} for e in result.errors
        ]
    
    return response


@router.get("/playground")
async def graphql_playground():
    """GraphQL Playground (简化版)"""
    return {
        "message": "Use /graphql endpoint with POST requests",
        "examples": {
            "list_cases": """{
                testCases(limit: 10) {
                    id
                    name
                    module
                    priority
                    status
                }
            }""",
            "list_bugs": """{
                bugs(status: "open", limit: 10) {
                    id
                    title
                    severity
                    status
                    reporter
                }
            }""",
            "create_case": """mutation {
                createTestCase(
                    name: "API Test"
                    module: "Auth"
                    priority: "P1"
                    caseType: "api"
                ) {
                    id
                    name
                    status
                }
            }"""
        }
    }