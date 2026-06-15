from app.services.swabi_client import swabi_client


async def get_all_activities():

    return await swabi_client.get(
        "/activity/get_all_activities?activityStatus=true&pageNumber=-1&pageSize=-1"
    )
    
async def search_activities(state=None,category=None):

    data = await get_all_activities()

    activities = data["data"]["content"]

    results = []

    for activity in activities:

        if state and activity["state"] != state:
            continue

        if category and activity["activityCategory"] != category:
            continue

        results.append(activity)

    return results
