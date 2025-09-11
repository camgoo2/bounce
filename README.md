## 📂 Project Structure

-`Backend/`
  -`main.py`
Not touching the ios through git, just in XCOde
-`iOS/`
  - `Bounce/`
    - `Models/` # Data models
    - `Preview Content/`
    - `Services/` # Networking & API calls
      - `APIService.swift`
    - `Views/` # UI screens
      - `HomeView.swift` #HomeScreen
      - `CreateBounceView.swift`#CreateBounceScreen
    - `BounceApp.swift` # App entry point
  - `BounceTests/`
  - `BounceUITests/`
- `README`

## Local Development  
1.Make a new environment
```conda env create -f env.yaml```
2.Activate the environment
```conda activate bounce```
3.Run poetry commands - this will create a lock file
`poetry config virtualenvs.create false`
`poetry install`



## API Testing
Running the local server

See swagger docs here http://127.0.0.1:8000/docs

(bounce-env) camgoodhue@Camerons-MacBook-Pro backend % uvicorn main:app --reload --host 0.0.0.0 --port 8000
INFO:     Will watch for changes in these directories: ['/Users/camgoodhue/Coding/bounce/backend']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [2505] using WatchFiles
INFO:     Started server process [2507]

Create Bounce
#Just using a in memory data base for  now while running. will update to persistent soon.





