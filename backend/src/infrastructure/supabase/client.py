import os
from supabase import acreate_client, AsyncClient, AsyncClientOptions

async def create_supabase_client() -> AsyncClient:
    return await acreate_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_KEY"],
        options=AsyncClientOptions(
            persist_session=False,
            auto_refresh_token=False,
        ),
    )