import requests, json, asyncio, discord
from dotenv import load_dotenv
from os import getenv

load_dotenv()
TOKEN = getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

#Fall 2026: 202690
#Summer 2026: 202660

def getClassByCRN(CRN, term="202690", params = None):
    
    if params is None: params={"txt_keywordany": CRN, "txt_term": term}
    else: term = params["txt_term"]

    print("Requesting: " + CRN)

    session = requests.Session()
    session.post("https://ssb.cc.binghamton.edu:8484/StudentRegistrationSsb/ssb/term/search?mode=search", data={"term": term})
    response = session.get("https://ssb.cc.binghamton.edu:8484/StudentRegistrationSsb/ssb/searchResults/searchResults", params=params).json()
    session.close()

    if response.get("data") is None: print("unsuccessful")
    else: print("successful")

    return response


async def checkIfCRNExists(crn):
    data = getClassByCRN(crn)
    if data.get("data") is None:
        return False
    if len(data["data"]) == 0:
        return False
    return data

async def checkinvalid(msg):
    if len(msg.content.split(" ")) != 2:
        await msg.channel.send("Please enter a CRN")
        return None        
    if not(msg.content.split(" ")[1].isdigit()) or len(msg.content.split(" ")[1]) != 5:
        await msg.channel.send("Invalid CRN")
        return None
    return msg.content.split(" ")[1]

async def classMsg(msg):
    crn = await checkinvalid(msg)
    
    if crn is None or not(data := await checkIfCRNExists(crn)):
        await msg.channel.send("Invalid CRN")
        return
    
    data = data["data"][0]
    await msg.channel.send(f"**{data["courseTitle"]} {data["subject"]} {data["courseDisplay"]}**" + 
                           f"\nMaximum Enrollment: **{data["maximumEnrollment"]}**" + 
                           f"\nSeats Available: **{data["seatsAvailable"]}**" +  
                           f"\n\nWaitlist Capacity: **{data["waitCapacity"]}**" + 
                           f"\nWaitlist Count: **{data["waitCount"]}**")

async def checkFound(msg, data):
    found = False
    for user in data["userdata"]:
        if user["userid"] == msg.author.id:
            found = True   

    if not(found):
        data["userdata"].append({
            "userid": msg.author.id,
            "stalkList": [],
            "seatsAvailable": []
        })   

async def stalklist(msg):
    with open("userdata.json", "r") as f: data = json.load(f)

    await checkFound(msg, data)

    with open("userdata.json", "w") as f:
        json.dump(data, f, indent=4)

    for user in data["userdata"]:
        if user["userid"] == msg.author.id:
            await msg.channel.send("Stalklist: \n" + "\n".join(user["stalkList"]))

async def stalk(msg):
    crn = await checkinvalid(msg)
    if crn is None or not(dat := await checkIfCRNExists(crn)):
        await msg.channel.send("Invalid CRN")
        return
    
    with open("userdata.json", "r") as f:
        data = json.load(f)

    await checkFound(msg, data)
    for user in data["userdata"]:
        if user["userid"] == msg.author.id:
            if not(crn in user["stalkList"]):
                user["stalkList"].append(crn)
                user["seatsAvailable"].append(dat["data"][0]["seatsAvailable"])
        
    with open("userdata.json", "w") as f:
        json.dump(data, f, indent=4)
    
    await stalklist(msg)
            
async def unstalk(msg):
    crn = await checkinvalid(msg)
    if crn is None:
        return
    
    with open("userdata.json", "r") as f:
        data = json.load(f)

    await checkFound(msg, data)

    for user in data["userdata"]:
        if user["userid"] == msg.author.id:
            if crn in user["stalkList"]:
                user["seatsAvailable"].pop(user["stalkList"].index(crn))
                user["stalkList"].remove(crn)
            else:
                await msg.channel.send("Not stalking class")

    with open("userdata.json", "w") as f:
        json.dump(data, f, indent=4)

    await stalklist(msg)

async def update():
    await client.wait_until_ready()
    while not client.is_closed():
        print("Running Update")
        with open("userdata.json", "r") as f:
            data = json.load(f)
        for user in data["userdata"]:
            for indx, CRN in enumerate(user["stalkList"]):
                nData = getClassByCRN(CRN)
                newSeatsAvailable = nData["data"][0]["seatsAvailable"]
                if (user["seatsAvailable"][indx] == 0) and newSeatsAvailable != 0:
                    a = await client.fetch_user(user["userid"])
                    await a.send("ALERT: SEATS IN CRN " + CRN + " WENT FROM 0 to " + str(newSeatsAvailable) + " <@" + str(user["userid"]) + ">")
                user["seatsAvailable"][indx] = newSeatsAvailable
        with open("userdata.json", "w") as f:
            json.dump(data, f, indent=4)
        await asyncio.sleep(600)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    client.loop.create_task(update())


@client.event
async def on_message(message):
    if message.content[0] == ".":
        match message.content.split(" ")[0][1:].lower():
            case "class":
                await classMsg(message)

            case "stalk":
                await stalk(message)

            case "unstalk":
                await unstalk(message)

            case "stalklist":
                await stalklist(message)
def main():
    client.run(TOKEN)

if __name__ == "__main__":
    main()