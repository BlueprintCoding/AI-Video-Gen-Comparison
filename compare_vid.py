import os
import sys
# Redirect stderr to suppress VLC and other library messages
sys.stderr = open(os.devnull, 'w')

import vlc
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
import threading
import subprocess
import json
import time

CONFIG_FILE = "config.json"
INPUT_DIR = "input"
OUTPUT_DIR = "output"
media_player_lock = threading.Lock()


class VideoComparerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Comparer")
        self.root.geometry("1300x650")

        # Load or initialize configuration
        self.config = self.load_config()

        # Ensure input and output directories exist
        os.makedirs(INPUT_DIR, exist_ok=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Configure main layout
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=3)  # Middle column (Video List)
        self.root.grid_columnconfigure(2, weight=2)  # Right column (Playback)

        # Left sidebar
        self.sidebar = ctk.CTkFrame(self.root)
        self.sidebar.grid(row=0, column=0, sticky="nswe")
        self.sidebar.grid_rowconfigure(7, weight=1)

        ctk.CTkLabel(self.sidebar, text="Menu", font=("Arial", 18)).grid(row=0, column=0, pady=10, sticky="ew")

        # Buttons for the sidebar
        self.open_input_button = ctk.CTkButton(self.sidebar, text="Open Input Folder", command=lambda: self.open_folder(INPUT_DIR))
        self.open_input_button.grid(row=1, column=0, pady=5, padx=10, sticky="ew")

        self.open_output_button = ctk.CTkButton(self.sidebar, text="Open Output Folder", command=lambda: self.open_folder(OUTPUT_DIR))
        self.open_output_button.grid(row=2, column=0, pady=5, padx=10, sticky="ew")

        self.compare_button = ctk.CTkButton(self.sidebar, text="Generate Comparison", command=self.generate_comparisons, state="disabled")
        self.compare_button.grid(row=4, column=0, pady=5, padx=10, sticky="ew")



        self.settings_button = ctk.CTkButton(self.sidebar, text="Settings", command=self.open_settings)
        self.settings_button.grid(row=6, column=0, pady=5, padx=10, sticky="ew")

        # Calculate maximum button width and set sidebar width
        max_button_width = max(
            button.winfo_reqwidth() for button in [
                self.open_input_button, self.open_output_button, 
                self.compare_button, self.settings_button
            ]
        ) + 20  # Add padding
        self.sidebar.configure(width=max_button_width)

        # Middle column: Video List
        self.video_list_frame = ctk.CTkFrame(self.root)
        self.video_list_frame.grid(row=0, column=1, sticky="nwe", padx=10, pady=10)
        self.video_list_frame.grid_rowconfigure(1, weight=1)  # Make rows flexible
        self.video_list_frame.grid_columnconfigure(0, weight=1)  # Make columns flexible

        # Label for the section
        ctk.CTkLabel(self.video_list_frame, text="Videos in Input Folder", font=("Arial", 16)).grid(row=0, column=0, pady=1)

        # "Check All" button
        self.check_all_button = ctk.CTkButton(
            self.video_list_frame,
            text="Check All",
            command=self.check_all_videos
        )
        self.check_all_button.grid(row=1, column=0, pady=1, padx=10, sticky="ew")

        # Refresh list button
        self.refresh_list_button = ctk.CTkButton(
            self.video_list_frame,
            text="Refresh List",
            command=self.refresh_video_list
        )
        self.refresh_list_button.grid(row=3, column=0, pady=1, padx=10, sticky="ew")

        # Make the scrollable frame dynamically resize
        self.video_listbox = ctk.CTkScrollableFrame(self.video_list_frame, height=500)
        self.video_listbox.grid(row=2, column=0, sticky="nswe", pady=1, padx=5)

        # Right column: Video Playback and Grading
        self.playback_frame = ctk.CTkFrame(self.root, width=300)
        self.playback_frame.grid(row=0, column=2, sticky="nwe", padx=10, pady=10)

        ctk.CTkLabel(self.playback_frame, text="Grade Videos", font=("Arial", 16)).grid(row=0, column=0, pady=2)
        # Create a nested frame for the buttons
        button_frame = ctk.CTkFrame(self.playback_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=2)

        # Add the Grade and Cancel buttons inside the nested frame
        self.grade_button = ctk.CTkButton(button_frame, text="Grade Checked Videos", command=self.start_grading, state="disabled")
        self.grade_button.pack(side="left", padx=5)

        cancel_button = ctk.CTkButton(button_frame, text="Cancel Grading", command=self.cancel_grading)
        cancel_button.pack(side="left", padx=5)

        self.canvas = ctk.CTkCanvas(self.playback_frame, bg="#2b2b2b", height=720, width=416)
        self.canvas.grid(row=2, column=0, pady=5)

        self.controls_frame = ctk.CTkFrame(self.playback_frame)
        self.controls_frame.grid(row=3, column=0, pady=10)

        ctk.CTkButton(self.controls_frame, text="Bad", command=lambda: self.mark_video("Bad")).grid(row=0, column=0, padx=5)
        ctk.CTkButton(self.controls_frame, text="Average", command=lambda: self.mark_video("Average")).grid(row=0, column=1, padx=5)
        ctk.CTkButton(self.controls_frame, text="Good", command=lambda: self.mark_video("Good")).grid(row=0, column=2, padx=5)
        ctk.CTkButton(self.controls_frame, text="Skip", command=self.skip_video).grid(row=0, column=3, padx=5)

        self.current_video_index = 0
        self.videos = []
        self.checkboxes = []
        self.stop_loop = threading.Event()
        self.media_player = None
        # Initialize VLC instance based on settings
        self.gpu_acceleration = self.config.get("gpu_acceleration", False)
        self.quiet_mode = self.config.get("quiet_mode", True)
        self.vlc_instance = self.create_vlc_instance()

        # Initial load of video list
        self.refresh_video_list()

    def create_vlc_instance(self):
        """Create VLC instance based on settings."""
        vlc_args = []
        if not self.gpu_acceleration:
            vlc_args.append("--avcodec-hw=none")
        if self.quiet_mode:
            vlc_args.append("--quiet")
        return vlc.Instance(" ".join(vlc_args))
    
    def check_all_videos(self):
        """Check all videos in the list."""
        for checkbox, var in zip(self.video_listbox.winfo_children(), self.checkboxes):
            var.set("on")  # Set the variable to "on"
            checkbox.select()  # Visually select the checkbox
        self.update_button_states()  # Update button states after checking all

    def load_config(self):
        """Load configuration from the config file."""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as file:
                return json.load(file)
        return {}

    def save_config(self):
        """Save the current configuration to the config file."""
        with open(CONFIG_FILE, "w") as file:
            json.dump(self.config, file, indent=4)

    def open_folder(self, folder_path):
        """Open the specified folder in the file explorer."""
        os.startfile(folder_path)

    def refresh_video_list(self):
        """Refresh the list of videos in the input folder."""
        self.videos = [
            os.path.join(INPUT_DIR, f) for f in os.listdir(INPUT_DIR)
            if f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov'))
        ]
        for widget in self.video_listbox.winfo_children():
            widget.destroy()

        self.checkboxes = []
        for video in self.videos:
            var = ctk.StringVar(value="off")
            var.trace("w", lambda *args: self.update_button_states())  # Add a trace listener
            checkbox = ctk.CTkCheckBox(
                self.video_listbox,
                text=os.path.basename(video),
                variable=var,
                onvalue=video,
                offvalue="off"
            )
            checkbox.pack(anchor="w", pady=2)
            self.checkboxes.append(var)


    def update_button_states(self):
        """Enable or disable buttons based on selections."""
        selected_videos = [var.get() for var in self.checkboxes if var.get() != "off"]
        # Enable compare button if 2-5 videos are selected
        if 2 <= len(selected_videos) <= 5:
            self.compare_button.configure(state="normal")
        else:
            self.compare_button.configure(state="disabled")

        # Enable grade button if at least 1 video is selected
        if len(selected_videos) > 0:
            self.grade_button.configure(state="normal")
        else:
            self.grade_button.configure(state="disabled")

    def get_selected_videos(self):
        """Get the list of selected videos."""
        return [var.get() for var in self.checkboxes if var.get() != "off"]

    def generate_comparisons(self):
        """Handle generating comparisons."""
        selected_videos = self.get_selected_videos()
        if len(selected_videos) < 2 or len(selected_videos) > 5:
            messagebox.showerror("Error", "Please select 2 to 5 videos for comparison.")
            return

        # Open a modal for text inputs
        self.open_comparison_modal(selected_videos)

    def open_comparison_modal(self, videos):
        """Open a modal window to get text overlays for videos."""
        # Create a modal window
        text_input_window = ctk.CTkToplevel(self.root)
        text_input_window.title("Enter Text Overlays")
        text_input_window.geometry("650x450")
        text_input_window.grab_set()  # Ensure the modal stays on top

        # Add a label for instructions
        ctk.CTkLabel(
            text_input_window, 
            text="Enter text to overlay on each video (leave blank if not needed):", 
            font=("Arial", 14)
        ).pack(pady=10)

        # Create a scrollable frame for the video list
        scrollable_frame = ctk.CTkScrollableFrame(text_input_window, width=580, height=250)
        scrollable_frame.pack(padx=10, pady=10, fill="both", expand=True)

        text_inputs = []  # Store input fields for text overlays
        for idx, video in enumerate(videos):
            frame = ctk.CTkFrame(scrollable_frame)
            frame.pack(pady=5, padx=5, fill="x")
            
            # Label for each video
            ctk.CTkLabel(frame, text=f"Video {idx + 1}: ({os.path.basename(video)}):", anchor="w").pack(side="left", padx=5)

            # Entry for text overlay
            text_var = ctk.StringVar()
            text_inputs.append(text_var)
            ctk.CTkEntry(frame, textvariable=text_var, width=250).pack(side="right", padx=5)

        # Add a submit button at the bottom of the modal
        def on_submit():
            text_input_window.destroy()
            self.compare_videos(videos, text_inputs)

        ctk.CTkButton(text_input_window, text="Submit", command=on_submit).pack(pady=10)


    def compare_videos(self, videos, text_inputs):
        """Generate a side-by-side comparison video with proper aspect ratio and labels."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_subdir = os.path.join(
            OUTPUT_DIR, f"{timestamp}_{os.path.basename(videos[0])[:-4]}"
        )
        os.makedirs(output_subdir, exist_ok=True)

        output_file = os.path.join(output_subdir, "comparison.mp4")

        durations = []
        frame_rates = []
        for file in videos:
            duration_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file]
            duration_result = subprocess.run(duration_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            durations.append(float(duration_result.stdout.strip()))

            frame_rate_cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "default=noprint_wrappers=1:nokey=1", file]
            frame_rate_result = subprocess.run(frame_rate_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            frame_rate = eval(frame_rate_result.stdout.strip())
            frame_rates.append(frame_rate)

        shortest_duration = min(durations)
        max_frame_rate = max(frame_rates)
        speed_factors = [duration / shortest_duration for duration in durations]

        filters = []
        for i, (speed, text_var) in enumerate(zip(speed_factors, text_inputs)):
            padded_height = "ih+50"
            text_overlay = f",drawtext=fontfile=/path/to/font.ttf:fontsize=24:fontcolor=white:x=(w-text_w)/2:y=h-40:text='{text_var.get()}'" if text_var.get() else ""
            filters.append(f"[{i}:v]fps={max_frame_rate},scale=trunc(iw/2)*2:trunc(ih/2)*2,pad=iw:{padded_height}:0:0:black,setpts=PTS/{speed}{text_overlay}[v{i}]")

        filter_graph = ";".join(filters) + f";{''.join(f'[v{i}]' for i in range(len(videos)))}hstack=inputs={len(videos)}"
        ffmpeg_cmd = [
            "ffmpeg",
            *[arg for video in videos for arg in ("-i", video)],
            "-filter_complex", filter_graph,
            "-map", "0:a?",
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "fast",
            output_file
        ]

        try:
            subprocess.run(ffmpeg_cmd, check=True)
            self.show_video_player(output_file, videos, output_subdir, text_inputs)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"FFmpeg error: {e}")

        for video in videos:
            os.rename(video, os.path.join(output_subdir, os.path.basename(video)))

    def show_video_player(self, output_file, videos, output_subdir,labels):
        """Show the video player with scrubbing, notes, and a best video selection."""
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Extract video resolution
        resolution_cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", output_file
        ]
        resolution_result = subprocess.run(
            resolution_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        try:
            video_width, video_height = map(int, resolution_result.stdout.strip().split(','))
        except ValueError:
            video_width, video_height = 800, 600  # Default size

        # Scale video to fit within the screen
        padding = 50  # Add padding to ensure all controls fit
        scale_factor = min(screen_width / video_width, (screen_height - padding) / video_height, 1)
        window_width = int(video_width * scale_factor)
        window_height = int(video_height * scale_factor + padding)

        # Ensure the window height fits within the screen
        window_height = min(window_height, screen_height - 50)

        # Center horizontally and align to the top with some padding
        x_position = (screen_width - window_width) // 2
        y_position = 30  # Align slightly below the top of the screen

        player_window = ctk.CTkToplevel(self.root)
        player_window.title("Video Playback and Best Video Selection")
        player_window.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        player_window.rowconfigure(0, weight=1)
        player_window.columnconfigure(0, weight=1)

        vlc_instance = vlc.Instance("--avcodec-hw=none")
        media_player = vlc_instance.media_player_new()
        media = vlc_instance.media_new(output_file)
        media_player.set_media(media)

        # Video playback area
        video_frame = ctk.CTkFrame(player_window)
        video_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
        canvas = ctk.CTkCanvas(video_frame, width=video_width, height=video_height)
        canvas.pack(expand=True, fill="both")

        media_player.set_hwnd(canvas.winfo_id())

        # Controls
        controls_frame = ctk.CTkFrame(player_window)
        controls_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)

        is_scrubbing = ctk.BooleanVar(value=False)
        is_at_end = ctk.BooleanVar(value=False)

        def reload_media():
            """Reload the media to reset playback."""
            media_player.stop()
            media_player.set_media(media)
            media_player.play()
            is_at_end.set(False)

        def play_video():
            if is_at_end.get():
                reload_media()
            else:
                media_player.play()

        def pause_video():
            media_player.pause()

        def stop_video():
            media_player.stop()
            is_at_end.set(False)

        play_button = ctk.CTkButton(controls_frame, text="Play", command=play_video)
        play_button.pack(side="left", padx=5, pady=2)

        pause_button = ctk.CTkButton(controls_frame, text="Pause", command=pause_video)
        pause_button.pack(side="left", padx=5, pady=2)

        stop_button = ctk.CTkButton(controls_frame, text="Stop", command=stop_video)
        stop_button.pack(side="left", padx=5, pady=2)

        duration_slider = ctk.CTkSlider(
            controls_frame, from_=0, to=100, orientation="horizontal", width=400
        )
        duration_slider.pack(side="left", padx=5, pady=2)

        def update_slider():
            while True:
                try:
                    if not is_scrubbing.get():
                        current_time = media_player.get_time() // 1000
                        duration = media_player.get_length() // 1000
                        if duration > 0:
                            duration_slider.configure(to=duration)
                            duration_slider.set(current_time)
                    time.sleep(0.1)
                except Exception:
                    break

        def on_scrub_start(event):
            is_scrubbing.set(True)

        def on_scrub_end(event):
            is_scrubbing.set(False)
            scrub_time = int(duration_slider.get() * 1000)
            if is_at_end.get():
                reload_media()
            media_player.set_time(scrub_time)

        duration_slider.bind("<ButtonPress-1>", on_scrub_start)
        duration_slider.bind("<ButtonRelease-1>", on_scrub_end)

        def on_media_end(event):
            is_at_end.set(True)
            duration_slider.set(media_player.get_length() // 1000)

        media_player.event_manager().event_attach(vlc.EventType.MediaPlayerEndReached, on_media_end)

        # Best Video Checkboxes and Notes Section
        checkboxes_frame = ctk.CTkFrame(player_window)
        checkboxes_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ctk.CTkLabel(checkboxes_frame, text="Select the Best Video", font=("Arial", 14)).pack(pady=5)

        best_video_var = ctk.StringVar(value="")
        checkbox_inner_frame = ctk.CTkFrame(checkboxes_frame)
        checkbox_inner_frame.pack()

        for idx, video in enumerate(videos):
            user_label = labels[idx].get()  # Get the user-defined label
            checkbox_text = f"# {idx + 1} | {user_label} | {os.path.basename(video)}" if user_label else f"# {idx + 1} | {os.path.basename(video)}"
            checkbox = ctk.CTkCheckBox(
                checkbox_inner_frame,
                text=checkbox_text,
                variable=best_video_var,
                onvalue=video,
                offvalue=""
            )
            checkbox.pack(anchor="w", padx=5, pady=2)

        notes_label = ctk.CTkLabel(player_window, text="Notes:", font=("Arial", 14))
        notes_label.grid(row=3, column=0, columnspan=2, pady=5)

        notes_text = ctk.CTkTextbox(player_window, height=100)
        notes_text.grid(row=4, column=0, columnspan=2, pady=10, padx=10, sticky="ew")

        def save_notes():
            selected_video = best_video_var.get()
            notes = notes_text.get("1.0", "end").strip()
            if not selected_video:
                messagebox.showerror("Error", "Please select the best video.")
                return

            # Generate notes file path
            notes_file = os.path.join(output_subdir, "comparison_notes.txt")
            try:
                # Save the notes
                with open(notes_file, "w") as file:
                    file.write(f"Best Video: {os.path.basename(selected_video)}\n")
                    file.write(f"Notes:\n{notes}")
                
                # Add "best-" prefix to the selected video's filename
                selected_video_path = os.path.join(output_subdir, os.path.basename(selected_video))
                new_video_path = os.path.join(output_subdir, f"best-{os.path.basename(selected_video)}")

                # Check if the video exists in the output directory
                if os.path.exists(selected_video_path):
                    os.rename(selected_video_path, new_video_path)
                    messagebox.showinfo(
                        "Saved",
                        f"Notes saved to {notes_file}.\nBest video renamed to: {os.path.basename(new_video_path)}"
                    )
                else:
                    messagebox.showwarning(
                        "Warning",
                        f"The video file for '{selected_video}' was not found in the output directory. Only notes were saved."
                    )

                # Close the player window after saving
                player_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save notes: {e}")


        def delete_comparison():
            try:
                media_player.stop()
                media_player.release()
                for root, dirs, files in os.walk(output_subdir, topdown=False):
                    for file in files:
                        os.remove(os.path.join(root, file))
                    for dir in dirs:
                        os.rmdir(os.path.join(root, dir))
                os.rmdir(output_subdir)
                messagebox.showinfo("Deleted", f"Comparison folder '{output_subdir}' has been deleted.")
                player_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete folder: {e}")

        buttons_frame = ctk.CTkFrame(player_window)
        buttons_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")

        save_button = ctk.CTkButton(buttons_frame, text="Save Notes", command=save_notes)
        save_button.pack(side="left", padx=5)

        delete_button = ctk.CTkButton(buttons_frame, text="Delete Comparison", command=delete_comparison)
        delete_button.pack(side="right", padx=5)

        media_player.play()
        threading.Thread(target=update_slider, daemon=True).start()


    def start_grading(self):
        """Initialize the video grading process."""
        selected_videos = self.get_selected_videos()
        if not selected_videos:
            messagebox.showerror("Error", "No videos selected for grading.")
            return

        # Create the graded folder with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d - %I-%M %p")
        self.graded_folder = os.path.join(OUTPUT_DIR, f"Graded - {timestamp}")
        os.makedirs(self.graded_folder, exist_ok=True)

        # Reset state
        self.videos_to_grade = selected_videos
        self.current_video_index = 0
        self.stop_loop.clear()

        # Initialize VLC player
        self.media_player = self.vlc_instance.media_player_new()
        self.media_player.set_hwnd(self.canvas.winfo_id())

        self.play_video()

    def play_video(self):
        """Play the current video."""
        if self.current_video_index < len(self.videos_to_grade):
            self.current_video_path = self.videos_to_grade[self.current_video_index]
            print(f"Playing video: {self.current_video_path}")
    
            # Load and play the media
            self.load_and_play_media(self.current_video_path)
        else:
            self.finish_grading()

    def clear_media_player_events(self):
        if self.media_player:
            event_manager = self.media_player.event_manager()
            event_manager.event_detach(vlc.EventType.MediaPlayerEndReached)

    def release_media_player(self):
        if self.media_player:
            self.media_player.stop()
            self.media_player.release()
            self.media_player = None




    def load_and_play_media(self, video_path):
        """Load and start playing a video."""
        self.clear_media_player_events()
        self.release_media_player()

                # Initialize VLC player
        self.media_player = self.vlc_instance.media_player_new()
        self.media_player.set_hwnd(self.canvas.winfo_id())

        with media_player_lock:
            # Stop the player and clear any previous media
            if self.media_player:
                self.media_player.stop()
                self.media_player.set_media(None)  # Release any previously loaded media

            # Create a new media object and load it
            media = self.vlc_instance.media_new(video_path)
            self.media_player.set_media(media)

            # Attach the MediaPlayerEndReached event
            self.media_player.event_manager().event_attach(
                vlc.EventType.MediaPlayerEndReached, self.restart_video
            )

            # Start playback
            result = self.media_player.play()
            if result == 0:
                print(f"Video started successfully: {video_path}")
            else:
                print(f"Failed to start video. Result: {result}")


    def restart_video(self, event=None):
        """Restart the current video."""
        print("Video ended. Restarting...")

        # Rebuild the canvas before proceeding
        self.rebuild_canvas()

        if self.current_video_index < len(self.videos_to_grade):
            video_path = self.videos_to_grade[self.current_video_index]
            print(f"Restarting video: {video_path}")
            self.load_and_play_media(video_path)
        else:
            print("No video to restart. Grading might be complete.")


    def rebuild_canvas(self):
        """Destroy and recreate the video canvas."""
        print("Rebuilding video canvas...")
        if self.canvas:
            self.canvas.destroy()

        self.canvas = ctk.CTkCanvas(self.playback_frame, bg="#2b2b2b", height=720, width=416)
        self.canvas.grid(row=2, column=0, pady=5)

        # Reinitialize the media player with the new canvas
        with media_player_lock:
            self.media_player = self.vlc_instance.media_player_new()
            self.media_player.set_hwnd(self.canvas.winfo_id())
        print("Canvas rebuilt and media player reattached.")


    def skip_video(self):
        """Skip the current video."""
        self.current_video_index += 1
        self.play_video()


    def mark_video(self, grade):
        """Grade the current video."""
        video_path = self.videos_to_grade[self.current_video_index]
        grade_folder = os.path.join(self.graded_folder, grade)
        os.makedirs(grade_folder, exist_ok=True)

        try:
            # Stop and release the media player
            with media_player_lock:
                if self.media_player:
                    self.media_player.stop()
                    self.media_player.set_media(None)  # Release the media object

            # Move the video to the graded folder
            os.rename(video_path, os.path.join(grade_folder, os.path.basename(video_path)))
            print(f"Video moved to {grade_folder}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to move video: {e}")
            return

        # Proceed to the next video
        self.current_video_index += 1
        self.play_video()


    def finish_grading(self):
        """Finalize grading process."""
        self.media_player.stop()
        messagebox.showinfo("Completed", f"All videos graded and moved to:\n{self.graded_folder}")
        self.refresh_video_list()


    def cancel_grading(self):
        """Cancel the grading process and restore videos to the input folder."""
        if not hasattr(self, 'graded_folder') or not os.path.exists(self.graded_folder):
            messagebox.showerror("Error", "No grading process to cancel.")
            return

        try:
            # Move videos back to the input folder
            for grade_folder in os.listdir(self.graded_folder):
                grade_path = os.path.join(self.graded_folder, grade_folder)
                if os.path.isdir(grade_path):
                    for video in os.listdir(grade_path):
                        video_path = os.path.join(grade_path, video)
                        os.rename(video_path, os.path.join(INPUT_DIR, video))
            
            # Delete the graded folder
            for root, dirs, files in os.walk(self.graded_folder, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(self.graded_folder)

            # Reset the state and UI
            self.current_video_index = 0
            self.videos_to_grade = []
            self.graded_folder = None
            self.stop_loop.set()
            if self.media_player:
                self.media_player.stop()
            self.refresh_video_list()
            messagebox.showinfo("Cancelled", "Grading process has been cancelled and videos restored to input folder.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to cancel grading: {e}")


    def open_settings(self):
        """Open the settings window."""
        settings_window = ctk.CTkToplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x300")
        
        # Ensure the settings modal stays on top and grabs focus
        settings_window.grab_set()
        settings_window.focus_set()

        # VLC Path
        ctk.CTkLabel(settings_window, text="VLC Path:", font=("Arial", 12)).pack(pady=10)
        vlc_path_var = ctk.StringVar(value=self.config.get("vlc_path", ""))
        ctk.CTkEntry(settings_window, textvariable=vlc_path_var, width=300).pack(pady=10)

        # GPU Acceleration Toggle
        gpu_toggle_var = ctk.BooleanVar(value=self.gpu_acceleration)
        ctk.CTkCheckBox(
            settings_window,
            text="Enable GPU Acceleration",
            variable=gpu_toggle_var
        ).pack(pady=10)

        # Quiet Mode Toggle
        quiet_toggle_var = ctk.BooleanVar(value=self.quiet_mode)
        ctk.CTkCheckBox(
            settings_window,
            text="Enable Quiet Mode (Suppress Logs)",
            variable=quiet_toggle_var
        ).pack(pady=10)

        # Save Button
        ctk.CTkButton(
            settings_window,
            text="Save",
            command=lambda: self.save_settings(vlc_path_var.get(), gpu_toggle_var.get(), quiet_toggle_var.get())
        ).pack(pady=20)


    def save_settings(self, vlc_path, gpu_acceleration, quiet_mode):
        """Save settings and reinitialize VLC instance if needed."""
        if not os.path.exists(os.path.join(vlc_path, "libvlc.dll")):
            messagebox.showerror("Error", "Invalid VLC path. Make sure it contains 'libvlc.dll'.")
            return

        # Update configuration
        self.config["vlc_path"] = vlc_path
        self.config["gpu_acceleration"] = gpu_acceleration
        self.config["quiet_mode"] = quiet_mode

        # Reinitialize VLC instance if settings changed
        if self.gpu_acceleration != gpu_acceleration or self.quiet_mode != quiet_mode:
            self.gpu_acceleration = gpu_acceleration
            self.quiet_mode = quiet_mode
            self.vlc_instance = self.create_vlc_instance()

        self.save_config()
        messagebox.showinfo("Saved", "Settings have been saved successfully.")


if __name__ == "__main__":
    ctk.set_appearance_mode("System")  # Modes: "System", "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue", "dark-blue", "green"

    root = ctk.CTk()
    app = VideoComparerApp(root)
    root.mainloop()
