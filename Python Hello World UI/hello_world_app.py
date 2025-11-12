#!/usr/bin/env python3
"""
Beautiful Hello World GUI Application
A simple yet elegant GUI app that displays "Hello World" in a pretty way when you click a button.
"""

import tkinter as tk
from tkinter import font
import random


class HelloWorldApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hello World App")
        self.root.geometry("600x400")
        self.root.configure(bg="#2C3E50")

        # Color palettes for the hello world text
        self.colors = [
            "#E74C3C", "#3498DB", "#2ECC71", "#F39C12",
            "#9B59B6", "#1ABC9C", "#E67E22", "#16A085"
        ]

        # Title label
        self.title_label = tk.Label(
            root,
            text="✨ Welcome to Hello World ✨",
            font=("Helvetica", 20, "bold"),
            bg="#2C3E50",
            fg="#ECF0F1"
        )
        self.title_label.pack(pady=30)

        # Frame to hold the hello world text
        self.text_frame = tk.Frame(root, bg="#2C3E50")
        self.text_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Hello World label (initially hidden)
        self.hello_label = tk.Label(
            self.text_frame,
            text="",
            font=("Helvetica", 48, "bold"),
            bg="#2C3E50",
            fg="#ECF0F1"
        )
        self.hello_label.pack(expand=True)

        # Button frame
        self.button_frame = tk.Frame(root, bg="#2C3E50")
        self.button_frame.pack(pady=20)

        # Show Hello World button
        self.show_button = tk.Button(
            self.button_frame,
            text="🌟 Click Me! 🌟",
            font=("Helvetica", 16, "bold"),
            bg="#3498DB",
            fg="white",
            activebackground="#2980B9",
            activeforeground="white",
            relief="raised",
            bd=3,
            padx=30,
            pady=15,
            cursor="hand2",
            command=self.show_hello_world
        )
        self.show_button.pack(side="left", padx=10)

        # Clear button
        self.clear_button = tk.Button(
            self.button_frame,
            text="Clear",
            font=("Helvetica", 12),
            bg="#95A5A6",
            fg="white",
            activebackground="#7F8C8D",
            activeforeground="white",
            relief="raised",
            bd=3,
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.clear_text
        )
        self.clear_button.pack(side="left", padx=10)

        # Animation variables
        self.is_animating = False
        self.animation_step = 0

    def show_hello_world(self):
        """Display Hello World with a fancy animation"""
        if not self.is_animating:
            self.is_animating = True
            self.animation_step = 0
            self.animate_hello_world()

    def animate_hello_world(self):
        """Animate the Hello World text with color changes and scaling"""
        if self.animation_step < 10:
            # Change color randomly
            color = random.choice(self.colors)
            self.hello_label.config(fg=color)

            # Animate the text appearing
            texts = [
                "",
                "H",
                "He",
                "Hel",
                "Hell",
                "Hello",
                "Hello ",
                "Hello W",
                "Hello Wo",
                "Hello Wor",
                "Hello Worl",
                "Hello World",
                "Hello World!",
                "🎉 Hello World! 🎉"
            ]

            if self.animation_step < len(texts):
                self.hello_label.config(text=texts[self.animation_step])

            self.animation_step += 1
            self.root.after(100, self.animate_hello_world)
        else:
            self.is_animating = False
            # Start color pulse animation
            self.pulse_colors()

    def pulse_colors(self):
        """Continuously pulse through colors"""
        if self.hello_label.cget("text"):
            color = random.choice(self.colors)
            self.hello_label.config(fg=color)
            self.root.after(500, self.pulse_colors)

    def clear_text(self):
        """Clear the Hello World text"""
        self.hello_label.config(text="")
        self.is_animating = False
        self.animation_step = 0


def main():
    """Main function to run the application"""
    root = tk.Tk()
    app = HelloWorldApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
