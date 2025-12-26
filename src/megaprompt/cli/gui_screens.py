"""GUI screen implementations for MEGAPROMPT."""

import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter
import yaml

from megaprompt.cli.gui_theme import get_color
from megaprompt.core.cache import Cache
from megaprompt.core.checkpoint import CheckpointManager
from megaprompt.core.config import Config
from megaprompt.core.pipeline import MegaPromptPipeline


class BaseScreen(customtkinter.CTkScrollableFrame):
    """Base class for all screens."""
    
    def __init__(self, parent, app=None):
        super().__init__(
            parent,
            fg_color=get_color("background"),
            corner_radius=10,
        )
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        
    def _create_section(self, title: str, row: int) -> int:
        """Create a titled section and return next row."""
        title_label = customtkinter.CTkLabel(
            self,
            text=title,
            font=customtkinter.CTkFont(size=18, weight="bold"),
            text_color=get_color("primary"),
        )
        title_label.grid(row=row, column=0, padx=20, pady=(20, 10), sticky="w")
        return row + 1


class GenerateScreen(BaseScreen):
    """Screen for generating mega-prompts."""
    
    def __init__(self, parent, app=None):
        super().__init__(parent, app)
        self.pipeline: Optional[MegaPromptPipeline] = None
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the generate screen UI."""
        row = 0
        
        # Title
        row = self._create_section("Generate Mega-Prompt", row)
        
        # Input section
        input_label = customtkinter.CTkLabel(
            self,
            text="Input Prompt:",
            font=customtkinter.CTkFont(size=14, weight="bold"),
            text_color=get_color("foreground"),
        )
        input_label.grid(row=row, column=0, padx=20, pady=(10, 5), sticky="w")
        row += 1
        
        # Input text area
        self.input_text = customtkinter.CTkTextbox(
            self,
            height=150,
            fg_color=get_color("input_bg"),
            text_color=get_color("foreground"),
            corner_radius=10,
            border_width=1,
            border_color=get_color("border"),
        )
        self.input_text.grid(row=row, column=0, padx=20, pady=5, sticky="ew")
        row += 1
        
        # Input buttons
        input_buttons = customtkinter.CTkFrame(self, fg_color="transparent")
        input_buttons.grid(row=row, column=0, padx=20, pady=5, sticky="w")
        
        load_file_btn = customtkinter.CTkButton(
            input_buttons,
            text="Load File",
            command=self._load_file,
            fg_color=get_color("button_bg"),
            hover_color=get_color("button_hover"),
            width=100,
        )
        load_file_btn.pack(side="left", padx=5)
        
        clear_btn = customtkinter.CTkButton(
            input_buttons,
            text="Clear",
            command=self._clear_input,
            fg_color=get_color("button_bg"),
            hover_color=get_color("button_hover"),
            width=100,
        )
        clear_btn.pack(side="left", padx=5)
        row += 1
        
        # Configuration section
        row = self._create_section("Configuration", row)
        
        config_frame = customtkinter.CTkFrame(
            self,
            fg_color=get_color("surface"),
            corner_radius=10,
        )
        config_frame.grid(row=row, column=0, padx=20, pady=10, sticky="ew")
        config_frame.grid_columnconfigure(1, weight=1)
        row += 1
        
        # Provider
        customtkinter.CTkLabel(
            config_frame,
            text="Provider:",
            text_color=get_color("foreground"),
        ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.provider_var = customtkinter.StringVar(value="auto")
        provider_menu = customtkinter.CTkOptionMenu(
            config_frame,
            values=["auto", "ollama", "qwen", "gemini"],
            variable=self.provider_var,
            fg_color=get_color("button_bg"),
            button_hover_color=get_color("button_hover"),
        )
        provider_menu.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Model
        customtkinter.CTkLabel(
            config_frame,
            text="Model:",
            text_color=get_color("foreground"),
        ).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.model_entry = customtkinter.CTkEntry(
            config_frame,
            placeholder_text="Leave empty for default",
            fg_color=get_color("input_bg"),
            border_color=get_color("border"),
        )
        self.model_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        # Temperature
        customtkinter.CTkLabel(
            config_frame,
            text="Temperature:",
            text_color=get_color("foreground"),
        ).grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.temp_entry = customtkinter.CTkEntry(
            config_frame,
            placeholder_text="0.0",
            fg_color=get_color("input_bg"),
            border_color=get_color("border"),
        )
        self.temp_entry.insert(0, "0.0")
        self.temp_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        
        # API Key
        customtkinter.CTkLabel(
            config_frame,
            text="API Key:",
            text_color=get_color("foreground"),
        ).grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.api_key_entry = customtkinter.CTkEntry(
            config_frame,
            placeholder_text="Optional (uses env vars if empty)",
            fg_color=get_color("input_bg"),
            border_color=get_color("border"),
            show="*",
        )
        self.api_key_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        
        # Output format
        customtkinter.CTkLabel(
            config_frame,
            text="Output Format:",
            text_color=get_color("foreground"),
        ).grid(row=4, column=0, padx=10, pady=10, sticky="w")
        self.format_var = customtkinter.StringVar(value="markdown")
        format_menu = customtkinter.CTkOptionMenu(
            config_frame,
            values=["markdown", "json", "yaml"],
            variable=self.format_var,
            fg_color=get_color("button_bg"),
            button_hover_color=get_color("button_hover"),
        )
        format_menu.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
        
        # Options
        self.resume_var = customtkinter.BooleanVar(value=False)
        resume_check = customtkinter.CTkCheckBox(
            config_frame,
            text="Resume from checkpoint",
            variable=self.resume_var,
            fg_color=get_color("primary"),
            hover_color=get_color("button_hover"),
        )
        resume_check.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        
        # Generate button
        generate_btn = customtkinter.CTkButton(
            self,
            text="Generate Mega-Prompt",
            command=self._generate,
            fg_color=get_color("primary"),
            hover_color=get_color("button_hover"),
            height=50,
            font=customtkinter.CTkFont(size=16, weight="bold"),
        )
        generate_btn.grid(row=row, column=0, padx=20, pady=20, sticky="ew")
        row += 1
        
        # Progress bar
        self.progress_bar = customtkinter.CTkProgressBar(self)
        self.progress_bar.grid(row=row, column=0, padx=20, pady=10, sticky="ew")
        self.progress_bar.set(0)
        row += 1
        
        # Status label
        self.status_label = customtkinter.CTkLabel(
            self,
            text="Ready",
            text_color=get_color("text_muted"),
        )
        self.status_label.grid(row=row, column=0, padx=20, pady=5)
        row += 1
        
        # Results section
        row = self._create_section("Results", row)
        
        self.results_text = customtkinter.CTkTextbox(
            self,
            height=200,
            fg_color=get_color("input_bg"),
            text_color=get_color("foreground"),
            corner_radius=10,
            border_width=1,
            border_color=get_color("border"),
        )
        self.results_text.grid(row=row, column=0, padx=20, pady=10, sticky="ew")
        row += 1
        
        # Results buttons
        results_buttons = customtkinter.CTkFrame(self, fg_color="transparent")
        results_buttons.grid(row=row, column=0, padx=20, pady=5, sticky="w")
        
        save_btn = customtkinter.CTkButton(
            results_buttons,
            text="Save Results",
            command=self._save_results,
            fg_color=get_color("button_bg"),
            hover_color=get_color("button_hover"),
            width=120,
        )
        save_btn.pack(side="left", padx=5)
        
        copy_btn = customtkinter.CTkButton(
            results_buttons,
            text="Copy to Clipboard",
            command=self._copy_results,
            fg_color=get_color("button_bg"),
            hover_color=get_color("button_hover"),
            width=150,
        )
        copy_btn.pack(side="left", padx=5)
        
    def _load_file(self):
        """Load input from file."""
        filename = filedialog.askopenfilename(
            title="Select Input File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    content = f.read()
                self.input_text.delete("1.0", "end")
                self.input_text.insert("1.0", content)
                self.status_label.configure(text=f"Loaded: {Path(filename).name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {e}")
    
    def _clear_input(self):
        """Clear input text."""
        self.input_text.delete("1.0", "end")
        
    def _generate(self):
        """Generate mega-prompt in background thread."""
        input_text = self.input_text.get("1.0", "end-1c").strip()
        if not input_text:
            messagebox.showwarning("Warning", "Please enter a prompt first.")
            return
        
        # Disable generate button
        self.progress_bar.set(0)
        self.status_label.configure(text="Initializing...", text_color=get_color("primary"))
        self.results_text.delete("1.0", "end")
        
        # Start generation in background thread
        thread = threading.Thread(target=self._generate_thread, args=(input_text,), daemon=True)
        thread.start()
        
    def _generate_thread(self, user_prompt: str):
        """Generate mega-prompt in background thread."""
        try:
            # Get configuration
            provider = self.provider_var.get()
            model = self.model_entry.get().strip() or None
            try:
                temperature = float(self.temp_entry.get().strip() or "0.0")
            except ValueError:
                temperature = 0.0
            api_key = self.api_key_entry.get().strip() or None
            resume = self.resume_var.get()
            
            # Create pipeline
            checkpoint_dir = Path.home() / ".megaprompt" / "checkpoints"
            cache_dir = Path.home() / ".megaprompt" / "cache"
            
            self.pipeline = MegaPromptPipeline(
                provider=provider,
                model=model,
                temperature=temperature,
                api_key=api_key,
                checkpoint_dir=checkpoint_dir,
                cache_dir=cache_dir,
                use_cache=True,
            )
            
            # Update progress
            self._update_status("Stage 1: Intent Extraction...", 0.2)
            
            # Generate
            output_format = self.format_var.get()
            mega_prompt, intermediate = self.pipeline.generate(
                user_prompt,
                verbose=True,
                resume=resume,
            )
            
            # Format output
            if output_format == "json":
                output = json.dumps(intermediate, indent=2)
            elif output_format == "yaml":
                output = yaml.dump(intermediate, default_flow_style=False)
            else:
                output = mega_prompt
            
            # Update UI
            self._update_status("Generation complete!", 1.0)
            self.results_text.delete("1.0", "end")
            self.results_text.insert("1.0", output)
            self._update_status("Ready", get_color("text_muted"))
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self._update_status(error_msg, 0.0, get_color("error"))
            self.results_text.delete("1.0", "end")
            self.results_text.insert("1.0", error_msg)
            messagebox.showerror("Generation Error", str(e))
    
    def _update_status(self, message: str, progress: float, color: Optional[str] = None):
        """Update status label and progress bar."""
        self.after(0, lambda: self.status_label.configure(
            text=message,
            text_color=color or get_color("text_muted"),
        ))
        self.after(0, lambda: self.progress_bar.set(progress))
    
    def _save_results(self):
        """Save results to file."""
        content = self.results_text.get("1.0", "end-1c")
        if not content.strip():
            messagebox.showwarning("Warning", "No results to save.")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Save Results",
            defaultextension=".md",
            filetypes=[
                ("Markdown", "*.md"),
                ("JSON", "*.json"),
                ("YAML", "*.yaml"),
                ("Text", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Results saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {e}")
    
    def _copy_results(self):
        """Copy results to clipboard."""
        content = self.results_text.get("1.0", "end-1c")
        if content.strip():
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo("Success", "Results copied to clipboard!")


class BatchScreen(BaseScreen):
    """Screen for batch processing."""
    
    def _setup_ui(self):
        """Setup the batch screen UI."""
        row = 0
        row = self._create_section("Batch Processing", row)
        
        # File selection
        file_label = customtkinter.CTkLabel(
            self,
            text="Select input files:",
            text_color=get_color("foreground"),
        )
        file_label.grid(row=row, column=0, padx=20, pady=10, sticky="w")
        row += 1
        
        self.file_listbox = tk.Listbox(
            self,
            bg=get_color("input_bg"),
            fg=get_color("foreground"),
            selectbackground=get_color("primary"),
            height=10,
        )
        self.file_listbox.grid(row=row, column=0, padx=20, pady=5, sticky="ew")
        row += 1
        
        file_buttons = customtkinter.CTkFrame(self, fg_color="transparent")
        file_buttons.grid(row=row, column=0, padx=20, pady=5, sticky="w")
        
        add_files_btn = customtkinter.CTkButton(
            file_buttons,
            text="Add Files",
            command=self._add_files,
            fg_color=get_color("button_bg"),
            hover_color=get_color("button_hover"),
        )
        add_files_btn.pack(side="left", padx=5)
        
        remove_file_btn = customtkinter.CTkButton(
            file_buttons,
            text="Remove Selected",
            command=self._remove_file,
            fg_color=get_color("button_bg"),
            hover_color=get_color("button_hover"),
        )
        remove_file_btn.pack(side="left", padx=5)
        row += 1
        
        # Process button
        process_btn = customtkinter.CTkButton(
            self,
            text="Process Batch",
            command=self._process_batch,
            fg_color=get_color("primary"),
            hover_color=get_color("button_hover"),
            height=50,
            font=customtkinter.CTkFont(size=16, weight="bold"),
        )
        process_btn.grid(row=row, column=0, padx=20, pady=20, sticky="ew")
        row += 1
        
        # Progress
        self.progress_bar = customtkinter.CTkProgressBar(self)
        self.progress_bar.grid(row=row, column=0, padx=20, pady=10, sticky="ew")
        row += 1
        
        self.status_label = customtkinter.CTkLabel(
            self,
            text="Ready",
            text_color=get_color("text_muted"),
        )
        self.status_label.grid(row=row, column=0, padx=20, pady=5)
        
    def _add_files(self):
        """Add files to batch list."""
        files = filedialog.askopenfilenames(
            title="Select Input Files",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        for file in files:
            self.file_listbox.insert("end", file)
    
    def _remove_file(self):
        """Remove selected file from list."""
        selection = self.file_listbox.curselection()
        for index in reversed(selection):
            self.file_listbox.delete(index)
    
    def _process_batch(self):
        """Process batch files."""
        files = list(self.file_listbox.get(0, "end"))
        if not files:
            messagebox.showwarning("Warning", "Please add files to process.")
            return
        
        # TODO: Implement batch processing
        messagebox.showinfo("Info", f"Batch processing {len(files)} files...")


class ConfigScreen(BaseScreen):
    """Screen for configuration management."""
    
    def _setup_ui(self):
        """Setup the config screen UI."""
        row = 0
        row = self._create_section("Configuration", row)
        
        info_label = customtkinter.CTkLabel(
            self,
            text="Configuration is loaded from:\n1. CLI arguments (highest priority)\n2. Project config (.megaprompt.yaml)\n3. User config (~/.megaprompt/config.yaml)\n4. Defaults (lowest priority)",
            text_color=get_color("text_muted"),
            justify="left",
        )
        info_label.grid(row=row, column=0, padx=20, pady=10, sticky="w")
        row += 1
        
        # Config editor
        self.config_text = customtkinter.CTkTextbox(
            self,
            height=300,
            fg_color=get_color("input_bg"),
            text_color=get_color("foreground"),
            corner_radius=10,
        )
        self.config_text.grid(row=row, column=0, padx=20, pady=10, sticky="ew")
        
        # Load current config
        try:
            config = Config.load()
            config_dict = config.to_dict()
            config_yaml = yaml.dump(config_dict, default_flow_style=False)
            self.config_text.insert("1.0", config_yaml)
        except Exception as e:
            self.config_text.insert("1.0", f"# Error loading config: {e}")
        
        row += 1
        
        # Buttons
        buttons = customtkinter.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=row, column=0, padx=20, pady=10, sticky="w")
        
        save_btn = customtkinter.CTkButton(
            buttons,
            text="Save Config",
            command=self._save_config,
            fg_color=get_color("primary"),
            hover_color=get_color("button_hover"),
        )
        save_btn.pack(side="left", padx=5)
        
        reload_btn = customtkinter.CTkButton(
            buttons,
            text="Reload",
            command=self._reload_config,
            fg_color=get_color("button_bg"),
            hover_color=get_color("button_hover"),
        )
        reload_btn.pack(side="left", padx=5)
    
    def _save_config(self):
        """Save configuration."""
        content = self.config_text.get("1.0", "end-1c")
        try:
            config_dict = yaml.safe_load(content)
            if not isinstance(config_dict, dict):
                raise ValueError("Invalid YAML format")
            
            # Save to user config
            config_path = Path.home() / ".megaprompt" / "config.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_dict, f, default_flow_style=False)
            
            messagebox.showinfo("Success", f"Configuration saved to {config_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")
    
    def _reload_config(self):
        """Reload configuration."""
        try:
            config = Config.load()
            config_dict = config.to_dict()
            config_yaml = yaml.dump(config_dict, default_flow_style=False)
            self.config_text.delete("1.0", "end")
            self.config_text.insert("1.0", config_yaml)
            messagebox.showinfo("Success", "Configuration reloaded")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reload config: {e}")


class CheckpointsScreen(BaseScreen):
    """Screen for viewing and managing checkpoints."""
    
    def _setup_ui(self):
        """Setup the checkpoints screen UI."""
        row = 0
        row = self._create_section("Checkpoints", row)
        
        # Checkpoint list
        self.checkpoint_listbox = tk.Listbox(
            self,
            bg=get_color("input_bg"),
            fg=get_color("foreground"),
            selectbackground=get_color("primary"),
            height=15,
        )
        self.checkpoint_listbox.grid(row=row, column=0, padx=20, pady=10, sticky="ew")
        row += 1
        
        # Buttons
        buttons = customtkinter.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=row, column=0, padx=20, pady=10, sticky="w")
        
        refresh_btn = customtkinter.CTkButton(
            buttons,
            text="Refresh",
            command=self._refresh_checkpoints,
            fg_color=get_color("button_bg"),
            hover_color=get_color("button_hover"),
        )
        refresh_btn.pack(side="left", padx=5)
        
        delete_btn = customtkinter.CTkButton(
            buttons,
            text="Delete Selected",
            command=self._delete_checkpoint,
            fg_color=get_color("error"),
            hover_color="#CC0000",
        )
        delete_btn.pack(side="left", padx=5)
        
        clear_btn = customtkinter.CTkButton(
            buttons,
            text="Clear All",
            command=self._clear_checkpoints,
            fg_color=get_color("error"),
            hover_color="#CC0000",
        )
        clear_btn.pack(side="left", padx=5)
        
        self._refresh_checkpoints()
    
    def _refresh_checkpoints(self):
        """Refresh checkpoint list."""
        self.checkpoint_listbox.delete(0, "end")
        checkpoint_dir = Path.home() / ".megaprompt" / "checkpoints"
        if checkpoint_dir.exists():
            for checkpoint_file in checkpoint_dir.glob("*.json"):
                self.checkpoint_listbox.insert("end", checkpoint_file.name)
    
    def _delete_checkpoint(self):
        """Delete selected checkpoint."""
        selection = self.checkpoint_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a checkpoint to delete.")
            return
        
        checkpoint_name = self.checkpoint_listbox.get(selection[0])
        checkpoint_path = Path.home() / ".megaprompt" / "checkpoints" / checkpoint_name
        
        if messagebox.askyesno("Confirm", f"Delete checkpoint {checkpoint_name}?"):
            try:
                checkpoint_path.unlink()
                self._refresh_checkpoints()
                messagebox.showinfo("Success", "Checkpoint deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete: {e}")
    
    def _clear_checkpoints(self):
        """Clear all checkpoints."""
        if messagebox.askyesno("Confirm", "Delete all checkpoints?"):
            checkpoint_dir = Path.home() / ".megaprompt" / "checkpoints"
            try:
                for checkpoint_file in checkpoint_dir.glob("*.json"):
                    checkpoint_file.unlink()
                self._refresh_checkpoints()
                messagebox.showinfo("Success", "All checkpoints cleared.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear: {e}")


class CacheScreen(BaseScreen):
    """Screen for cache management."""
    
    def _setup_ui(self):
        """Setup the cache screen UI."""
        row = 0
        row = self._create_section("Cache Management", row)
        
        # Cache info
        self.info_label = customtkinter.CTkLabel(
            self,
            text="",
            text_color=get_color("text_muted"),
            justify="left",
        )
        self.info_label.grid(row=row, column=0, padx=20, pady=10, sticky="w")
        row += 1
        
        # Buttons
        buttons = customtkinter.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=row, column=0, padx=20, pady=10, sticky="w")
        
        refresh_btn = customtkinter.CTkButton(
            buttons,
            text="Refresh Stats",
            command=self._refresh_stats,
            fg_color=get_color("button_bg"),
            hover_color=get_color("button_hover"),
        )
        refresh_btn.pack(side="left", padx=5)
        
        clear_btn = customtkinter.CTkButton(
            buttons,
            text="Clear Cache",
            command=self._clear_cache,
            fg_color=get_color("error"),
            hover_color="#CC0000",
        )
        clear_btn.pack(side="left", padx=5)
        
        self._refresh_stats()
    
    def _refresh_stats(self):
        """Refresh cache statistics."""
        cache_dir = Path.home() / ".megaprompt" / "cache"
        if cache_dir.exists():
            cache_files = list(cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)
            size_mb = total_size / (1024 * 1024)
            info = f"Cache Directory: {cache_dir}\n"
            info += f"Files: {len(cache_files)}\n"
            info += f"Total Size: {size_mb:.2f} MB"
        else:
            info = "Cache directory does not exist."
        
        self.info_label.configure(text=info)
    
    def _clear_cache(self):
        """Clear cache."""
        if messagebox.askyesno("Confirm", "Clear all cache?"):
            cache_dir = Path.home() / ".megaprompt" / "cache"
            try:
                if cache_dir.exists():
                    for cache_file in cache_dir.glob("*.json"):
                        cache_file.unlink()
                self._refresh_stats()
                messagebox.showinfo("Success", "Cache cleared.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear cache: {e}")


class HelpScreen(BaseScreen):
    """Screen for help and documentation."""
    
    def _setup_ui(self):
        """Setup the help screen UI."""
        row = 0
        row = self._create_section("Help & Documentation", row)
        
        help_text = """
MEGAPROMPT - Transform messy prompts into structured mega-prompts

USAGE:
1. Enter your prompt in the Generate screen
2. Configure provider, model, and other settings
3. Click "Generate Mega-Prompt" to process
4. View and save results

FEATURES:
- 5-stage pipeline for prompt refinement
- Support for Ollama, Qwen, and Gemini providers
- Checkpointing for resuming interrupted generations
- Caching to avoid redundant API calls
- Batch processing for multiple files

CONFIGURATION:
Configuration is loaded from (in priority order):
1. CLI arguments
2. Project config (.megaprompt.yaml)
3. User config (~/.megaprompt/config.yaml)
4. Defaults

PROVIDERS:
- Ollama: Local LLM (requires running Ollama server)
- Qwen: Alibaba Cloud DashScope API (requires QWEN_API_KEY)
- Gemini: Google AI Studio (requires GEMINI_API_KEY)

For more information, visit the project repository.
        """
        
        help_label = customtkinter.CTkLabel(
            self,
            text=help_text.strip(),
            text_color=get_color("foreground"),
            justify="left",
            font=customtkinter.CTkFont(size=12),
        )
        help_label.grid(row=row, column=0, padx=20, pady=10, sticky="w")

