# Hunyuan Ouput Video Comparer App

Video Comparer is a Python-based application that allows you to compare, grade, and annotate Hunyuan Videos (or any really) for easy comparison. It generates side-by-side comparison videos with optional text overlays and provides an interactive grading interface.

NOTE: This is in beta and might be a little janky, If you have issues with the windows not being correctly sized try changing the dimensions of the window on line 25 of compare_vids.py "[self.root.geometry("1300x650")]"
KNOWN BUGS: Occassionally crashes when a ton of videos are loaded and you manage to grade a video right as it loops. 

## Features

- Compare 2 to 5 videos side-by-side.
- Overlay custom text on each video.
- Generate comparison videos using FFmpeg.
- Grade videos with button clicks or key bindings (1 = Bad, 2 = Average, 3 = Good, . = Skip).
- Save comparison notes and select the best video.
- Configurable settings for VLC path, GPU acceleration, and quiet mode.
- Organized input (`input/`) and output (`output/`) directories.

## Requirements

- Python 3.6+
- FFmpeg installed and added to your system PATH.
- VLC installed.
- Python packages:
  - `python-vlc`
  - `customtkinter`
  - `tkinter` (bundled with Python)
  - `tkinterdnd2` (if drag-and-drop functionality is desired)

## Installation and Setup

1. **Clone or Download the Repository**

2. **Run the Batch File**  
   A batch file (`run_app.bat`) is provided to set up the virtual environment, install required packages, and launch the app.

   - **Double-click** `run_app.bat` or run it from the command prompt:
     ```batch
     run_app.bat
     ```
   - The batch file performs the following steps:
     - Checks for an internet connection.
     - Creates a virtual environment (`venv`) if it doesn't exist.
     - Activates the virtual environment.
     - Upgrades `pip` and installs the required packages.
     - Launches the application by running `compare_vid.py`.

3. **Manual Setup (Optional)**  
   If you prefer to set up the environment manually:
   - Create and activate a virtual environment:
     ```batch
     python -m venv venv
     call venv\Scripts\activate
     ```
   - Upgrade `pip` and install dependencies:
     ```batch
     pip install --upgrade pip
     pip install tk tkinterdnd2 python-vlc customtkinter
     ```
   - Run the main script:
     ```batch
     python compare_vid.py
     ```

## Project Structure

├── compare_vid.py # Main Python script for the Video Comparer App. ├── config.json # Configuration file (auto-generated on first run). ├── input/ # Directory for input videos. ├── output/ # Directory for generated comparisons and graded videos. ├── run_app.bat # Batch file for setup and launching the application. └── README.md # This readme file.


## Usage

1. **Prepare Videos:**  
   Place video files (supported formats: `.mp4`, `.avi`, `.mkv`, `.mov`) in the `input` folder.

2. **Launch the Application:**  
   Use the batch file (`run_app.bat`) to start the app.

3. **Generate Comparisons:**  
   - Select 2 to 5 videos from the list.
   - Click "Generate Comparison" to open the text overlay modal.
   - Enter optional text for each video and submit to generate a side-by-side comparison.

4. **Grading Videos:**  
   - Check videos and click "Grade Checked Videos" to start grading.
   - Use on-screen buttons or key bindings (1, 2, 3, .) to grade or skip videos.
   - Save notes and designate the best video after grading.

5. **Settings:**  
   Access the Settings window to configure:
   - VLC path (must include `libvlc.dll`).
   - GPU acceleration.
   - Quiet mode (suppress library logs).

## Troubleshooting

- **FFmpeg Issues:**  
  Ensure FFmpeg is installed and available in your system PATH.

- **VLC Path:**  
  Verify the correct VLC path is provided in the settings if the app fails to initialize the VLC instance.

- **Video Playback:**  
  Confirm that the required Python packages are installed and that videos are in supported formats.

## License

[Include license information here, if applicable.]

## Contact

For questions or support, please contact [Your Contact Information].