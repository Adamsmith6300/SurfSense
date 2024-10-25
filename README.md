

![surfheader](https://github.com/user-attachments/assets/3bb180df-008d-4bad-9d9a-f4308e6b6aff)


# SurfSense

Well when I’m browsing the internet or reading any files such as pdfs, docs or images, I see a lot of content—but remembering when and what you saved? Total brain freeze! That’s where SurfSense comes in. SurfSense is a Personal AI Assistant for anything you see (Social Media Chats, Calender Invites, Important Mails, Tutorials, Recipies and anything ) on the Internet or your files. Now, you’ll never forget anything. Easily capture your web browsing session and desired webpage content using an easy-to-use cross browser extension or upload your files to SurfSense. Then, ask your personal knowledge base anything about your saved content, and voilà—instant recall! 

# Video




https://github.com/user-attachments/assets/cc6a0c51-7de0-45cd-982d-21768dc2dd38





## Key Features

- 💡 **Idea**: Save any content you see on the internet in your own personal knowledge base.
- ⚙️ **Cross Browser Extension**: Save your browsing content from your favourite browser.
- 📁 **Multiple File Format Uploading Support**: Save content from your own personal files(Documents, images and more) to your own personal knowledge base .
- 🔍 **Powerful Search**: Quickly find anything in your saved content.
- 💬 **Chat with your Saved Content**: Interact in Natural Language with your saved Web Browsing Sessions and get cited answers.
- 🔔 **Local LLM Support**: Works Flawlessly with Ollama local LLMs.
- 🏠 **Self Hostable**: Open source and easy to deploy locally.
- 📊 **Advanced RAG Techniques**: Utilize the power of Advanced RAG Techniques.
- 🔟% **Cheap On Wallet**: Works Flawlessly with OpenAI gpt-4o-mini model and Ollama local LLMs.
- 🕸️ **No WebScraping**: Extension directly reads the data from DOM to get accurate data.

## How to get started?
---
**UPDATE 24 OCTOBER 2024:** 
- SurfSense now uses custom gpt-researcher agent to format responses.
- Added better markdown rendering to UI.


**UPDATE 8 OCTOBER 2024:** 
- SurfSense now lets you upload your own files such as pdfs, docx, images etc into your SurfSense Knowledge Base.
- SurfSense uses [Unstructured-IO](https://github.com/Unstructured-IO/unstructured) to support files.


**UPDATE 25 SEPTEMBER 2024:** 
 - Thanks [@hnico21](https://github.com/hnico21) for adding Docker Support

   
**UPDATE 20 SEPTEMBER 2024:** 

 - SurfSense now works on Hierarchical Indices.
 - Knowledge Graph dependency is removed for now until I find some better Graph RAG solutions.
 - Added support for Local LLMs

Until I find a good host for my backend you need to setup SurfSense locally for now. 

---

### Docker Setup

1. Setup `SurfSense-Frontend/.env` and `backend/.env`
2. Run `docker-compose build --no-cache`.
3. After building image run `docker-compose up -d`
4. Now connect the extension with docker live backend url by updating `ss-cross-browser-extension/.env` and building it.


---
### Backend

For authentication purposes, you’ll also need a PostgreSQL instance running on your machine.

**UPDATE** : SurfSense now supports uploading various file types. To enable this feature, please set up the Unstructured.io library. You can follow the setup guide here: https://github.com/Unstructured-IO/unstructured?tab=readme-ov-file#installing-the-library

Now lets setup the SurfSense BackEnd
1. Clone this repo.
2. Go to ./backend subdirectory.
3. Setup Python Virtual Environment
4. Run `pip install -r requirements.txt` to install all required dependencies.
5. Update/Make the required Environment variables in .env
 
|ENV VARIABLE|Description  |
|--|--|
| UNSTRUCTURED_API_KEY | Your Unstructured IO API Key. Use any value if running a local instance or file upload support isn't needed.|
| POSTGRES_DATABASE_URL | postgresql+psycopg2://user:pass@host:5432/database|
| API_SECRET_KEY | Can be any Random String value. Make Sure to remember it for as you need to send it in user registration request to Backend for security purposes.|


6. Backend is a FastAPI Backend so now just run the server on unicorn using command `uvicorn server:app --host 0.0.0.0 --port 8000`
7. If everything worked fine you should see screen like this.

![backend](https://i.ibb.co/542Vhqw/backendrunning.png)

---

### FrontEnd

For local frontend setup just fill out the `.env` file of frontend.

|ENV VARIABLE|DESCRIPTION|
|--|--|
| NEXT_PUBLIC_API_SECRET_KEY | Same String value your set for Backend |
| NEXT_PUBLIC_BACKEND_URL | Give hosted backend url here. Eg. `http://127.0.0.1:8000`|
| NEXT_PUBLIC_RECAPTCHA_SITE_KEY | Google Recaptcha v2 Client Key |
| RECAPTCHA_SECRET_KEY | Google Recaptcha v2 Server Key|

and run it using `pnpm run dev`

You should see your Next.js frontend running at `localhost:3000`

**Make sure to register an account from frontend so you can login to extension.**

---

### Extension

Extension is in plasmo framework which is a cross browser extension framework.

For building extension just fill out the `.env` file of frontend.

|ENV VARIABLE|DESCRIPTION|
|--|--|
| PLASMO_PUBLIC_BACKEND_URL| SurfSense Backend URL eg. "http://127.0.0.1:8000" |

Build the extension for your favorite browser using this guide: https://docs.plasmo.com/framework/workflows/build#with-a-specific-target 

When you load and start the extension you should see a Login page like this

![extension login](https://i.ibb.co/qkkR5Lt/extlogin.png)



After logging in you will need to fill your OpenAPI Key. Fill random value if you are using Ollama.


![ext-settings](https://github.com/user-attachments/assets/49d8aa30-0ae1-4065-b504-e7e84dfb0d19)


After Saving you should be able to use extension now.

![ext-home](https://github.com/user-attachments/assets/34c6dc54-6853-4ef5-a74e-03f7ab555e42)


|Options|Explanations|
|--|--|
| Search Space | Think of it like a category tag for the webpages you want to save.  |
| Clear Inactive History Sessions | It clears the saved content for Inactive Tab Sessions.  |
| Save Current Webpage Snapshot | Stores the current webpage session info into SurfSense history store|
| Save to SurfSense | Processes the SurfSense History Store & Initiates a Save Job |

4. Now just start browsing the Internet. Whatever you want to save any content take its Snapshot and save it to SurfSense. After Save Job is completed you are ready to ask anything about it to SurfSense 🧠.

6. Now go to SurfSense Dashboard After Logging in.

|DASHBOARD OPTIONS|DESCRIPTION|
|--|--|
| Playground | See saved documents and can have chat with multiple docs. |
| Search Space Chat | Used for questions about your content in particular search space.|
| Saved Chats | All your saved chats.|
| Settings | If you want to update your Open API key.|


## Screenshots

#### Search Spaces Chat (Ollama LLM)
![1](https://github.com/user-attachments/assets/1b60fa01-36dd-44d3-93d0-a179e10452f3)


#### Multiple Document Chat (Ollama LLM)

![multidocs-localllm](https://github.com/user-attachments/assets/453a4406-1757-47f2-83d3-faf1b08f3d9d)



##  Tech Stack

 - **Extenstion** : Manifest v3 on Plasmo
 - **BackEnd** : FastAPI with LangChain
 - **FrontEnd**: Next.js with Aceternity.

#### Architecture:
In Progress...........

## Future Work
- Implement Canvas. 
- Add support for file uploads QA. **[Done]**
- Shift to WebSockets for Streaming responses.
- Based on feedback, I will work on making it compatible with local models. **[Done]**
- Cross Browser Extension **[Done]**
- Critical Notifications **[Done | PAUSED]**
- Saving Chats **[Done]**
- Basic keyword search page for saved sessions **[Done]**
- Multi & Single Document Chat **[Done]**


## Contribute 

Contributions are very welcome! A contribution can be as small as a ⭐ or even finding and creating issues.
Fine-tuning the Backend is always desired.

