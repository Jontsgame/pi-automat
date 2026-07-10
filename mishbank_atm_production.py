#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   MishBank ATM UI – Raspberry Pi 5                           ║
║                      PRODUCTION VERSION – API READY                          ║
║                                                                              ║
║  Authentische Mishpit-Implementierung mit ECHTEM MishBank API                ║
║  - Verbunden mit mishpit.com/MishBank/api.php                               ║
║  - Vollständige Banking-Funktionalität                                       ║
║  - Servo motor Integration für Geldauszahlung                                ║
║  - Smooth Animations & High-Tech UI                                          ║
║                                                                              ║
║  TECH STACK:                                                                 ║
║  • Python 3.9+                                                              ║
║  • CustomTkinter (Modern UI)                                                ║
║  • requests (HTTP API calls)                                                 ║
║  • gpiozero (GPIO + Servo control)                                          ║
║  • Threading (Async operations)                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import font
import customtkinter as ctk
import threading
import time
from dataclasses import dataclass
from typing import Optional
import requests
import json

# ═══════════════════════════════════════════════════════════════════════════
# HARDWARE IMPORTS (Raspberry Pi 5 GPIO & Servo)
# ═══════════════════════════════════════════════════════════════════════════

try:
    from gpiozero import Servo, Device
    from gpiozero.pins.lgpio import LGPIOFactory
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("⚠️  WARNING: gpiozero not available. Running in simulation mode.")


# ═══════════════════════════════════════════════════════════════════════════
# MISHPIT COLOR PALETTE
# ═══════════════════════════════════════════════════════════════════════════

class MishpitColors:
    """Authentic Mishpit design system"""
    BACKGROUND = "#0a0e27"
    SECONDARY_BG = "#1f1f1f"
    ACCENT = "#2e7d32"
    ACCENT_LIGHT = "#4caf50"
    ACCENT_BRIGHT = "#76ff03"
    TEXT_PRIMARY = "#f0f0f0"
    TEXT_SECONDARY = "#888888"
    SUCCESS = "#4caf50"
    ERROR = "#ff6b6b"
    BORDER = "#444444"
    PANEL = "#111111"


# ═══════════════════════════════════════════════════════════════════════════
# MISHBANK API – PRODUCTION (Real HTTP Calls)
# ═══════════════════════════════════════════════════════════════════════════

class MishBankAPI:
    """
    Production API for MishBank ATM
    
    All requests go to: https://mishpit.com/MishBank/api.php
    Uses JSON request/response format
    Handles all banking operations
    """
    
    API_BASE = "https://mishpit.com/MishBank/api.php"
    TIMEOUT = 10  # 10 second timeout for requests
    
    @staticmethod
    def _make_request(action: str, data: dict) -> dict:
        """
        Make HTTP POST request to MishBank API
        
        Args:
            action: API action (verify_card, authenticate_pin, etc.)
            data: Additional data for the request
        
        Returns:
            API response as dict
        """
        try:
            payload = {"action": action, **data}
            
            print(f"📡 API Request: {action}")
            response = requests.post(
                MishBankAPI.API_BASE,
                json=payload,
                timeout=MishBankAPI.TIMEOUT
            )
            
            result = response.json()
            print(f"✅ API Response: {result.get('message', 'OK')}")
            return result
            
        except requests.exceptions.Timeout:
            print("❌ API Timeout (10s)")
            return {
                "success": False,
                "message": "❌ Verbindung zum Server fehlgeschlagen (Timeout)"
            }
        except requests.exceptions.ConnectionError:
            print("❌ API Connection Error")
            return {
                "success": False,
                "message": "❌ Kann API nicht erreichen. Prüfe Internet-Verbindung."
            }
        except Exception as e:
            print(f"❌ API Error: {str(e)}")
            return {
                "success": False,
                "message": f"❌ API Fehler: {str(e)}"
            }
    
    @staticmethod
    def verify_card(card_number: str) -> dict:
        return MishBankAPI._make_request("verify_card", {
            "card_number": card_number
        })
    
    @staticmethod
    def authenticate_pin(card_number: str, pin: str) -> dict:
        return MishBankAPI._make_request("authenticate_pin", {
            "card_number": card_number,
            "pin": pin
        })
    
    @staticmethod
    def withdraw(card_number: str, amount_tokens: float) -> dict:
        return MishBankAPI._make_request("withdraw", {
            "card_number": card_number,
            "amount_tokens": amount_tokens
        })
    
    @staticmethod
    def deposit(card_number: str, amount_tokens: float) -> dict:
        return MishBankAPI._make_request("deposit", {
            "card_number": card_number,
            "amount_tokens": amount_tokens
        })
    
    @staticmethod
    def get_balance(card_number: str) -> dict:
        return MishBankAPI._make_request("get_balance", {
            "card_number": card_number
        })


# ═══════════════════════════════════════════════════════════════════════════
# SERVO MOTOR CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════

class ServoController:
    """
    Controls SG90 Servo Motor on Raspberry Pi 5
    GPIO Pin: 17 (configurable)
    Purpose: Dispenses cash when withdraw is successful
    """
    
    def __init__(self, gpio_pin: int = 17):
        self.gpio_pin = gpio_pin
        self.servo = None
        self.is_initialized = False
        
        if HARDWARE_AVAILABLE:
            try:
                Device.pin_factory = LGPIOFactory()
                self.servo = Servo(gpio_pin)
                
                # Sofortiges Abschalten des Signals nach dem Start, um Jittern zu verhindern
                self.servo.detach()
                
                self.is_initialized = True
                print(f"✅ Servo initialized on GPIO pin {gpio_pin} and detached (no jitter)")
            except Exception as e:
                print(f"⚠️  Servo initialization failed: {e}")
                self.is_initialized = False
        else:
            print("⚠️  Servo running in simulation mode (no hardware available)")
    
    def dispense_cash(self) -> None:
        """
        Rotates servo one full cycle to simulate cash dispensing
        Duration: ~2 seconds (smooth rotation)
        """
        if not self.is_initialized:
            print("🎬 [SIMULATION] Servo rotation: 0° → 180° → 0°")
            return
        
        try:
            print("💰 Initiating cash dispense...")
            
            # Das Zuweisen eines Wertes schaltet das PWM-Signal automatisch wieder EIN
            # Rotation auf Maximalposition (180°)
            self.servo.value = 1
            time.sleep(1)
            
            # Zurück auf Minimalposition (0°)
            self.servo.value = -1
            time.sleep(1)
            
            # Neutralstellung (90°)
            self.servo.value = 0
            time.sleep(0.5) # Kurze Pause, damit der Servo die Mitte sicher erreicht
            
            # Signal sofort wieder AUSSCHALTEN, sobald die Bewegung fertig ist
            self.servo.detach()
            print("✅ Cash dispensed successfully (Servo detached)")
            
        except Exception as e:
            print(f"❌ Servo error: {e}")
            # Sicherheitshalber auch im Fehlerfall abschalten
            if self.servo:
                self.servo.detach()
    
    def cleanup(self) -> None:
        """Gracefully close servo connection"""
        if self.servo:
            try:
                self.servo.close()
                print("🔌 Servo cleaned up")
            except Exception as e:
                print(f"Servo cleanup error: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def tokens_to_eur(tokens: float) -> float:
    """Convert MishTokens to Euros (1€ = 100 tokens)"""
    return tokens / 100.0


def eur_to_tokens(eur: float) -> float:
    """Convert Euros to MishTokens (1€ = 100 tokens)"""
    return eur * 100.0


def format_currency(tokens: float) -> tuple:
    """
    Format currency for display
    Returns: (tokens_str, eur_str)
    Example: ("50000 💾", "500.00€")
    """
    eur = tokens_to_eur(tokens)
    return (f"{tokens:,.0f} 💾", f"{eur:.2f}€")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ATM APPLICATION
# ═══════════════════════════════════════════════════════════════════════════

class MishBankATM(ctk.CTk):
    """
    Complete MishBank ATM Interface
    - Production API integration
    - Authentic Mishpit design
    - Full banking workflows
    """
    
    def __init__(self):
        super().__init__()
		# Vollbild aktivieren (self statt root!)
        self.attributes('-fullscreen', True)
        self.bind("<Escape>", lambda event: self.attributes("-fullscreen", False))
        
        # Initialize servo controller
        self.servo = ServoController(gpio_pin=17)
        
        # Window configuration
        self.title("🏦 MishBank ATM")
        self.geometry("480x800")
        self.resizable(False, False)
        
        # Configure color scheme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.configure(fg_color=MishpitColors.BACKGROUND)
        
        # State variables
        self.current_card = None
        self.current_pin = None
        self.withdrawal_amount = 0
        self.deposit_amount = 0
        
        # Create main frame
        self.main_frame = ctk.CTkFrame(
            self,
            fg_color=MishpitColors.BACKGROUND,
            corner_radius=0
        )
        self.main_frame.pack(fill="both", expand=True)
        
        # Show home screen
        self.show_home_screen()
    
    def clear_frame(self) -> None:
        """Clear main frame for new screen"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()
    
    # ═════════════════════════════════════════════════════════════════════
    # SCREEN 1: HOME SCREEN
    # ═════════════════════════════════════════════════════════════════════
    
    def show_home_screen(self) -> None:
        """Main menu: Withdraw or Deposit"""
        self.clear_frame()
        
        # Header
        header = ctk.CTkFrame(self.main_frame, fg_color=MishpitColors.ACCENT)
        header.pack(fill="x", padx=0, pady=0, ipady=20)
        
        title = ctk.CTkLabel(
            header,
            text="🏦 MishBank ATM",
            font=("Courier New", 32, "bold"),
            text_color=MishpitColors.TEXT_PRIMARY
        )
        title.pack()
        
        subtitle = ctk.CTkLabel(
            header,
            text="Produktives Banking System",
            font=("Courier New", 14),
            text_color=MishpitColors.TEXT_PRIMARY
        )
        subtitle.pack()
        
        # Spacer
        spacer = ctk.CTkFrame(self.main_frame, fg_color=MishpitColors.BACKGROUND)
        spacer.pack(pady=40)
        
        # Button: Withdraw
        withdraw_btn = ctk.CTkButton(
            self.main_frame,
            text="💸 Geld abheben",
            font=("Courier New", 18, "bold"),
            fg_color=MishpitColors.ACCENT,
            hover_color=MishpitColors.ACCENT_LIGHT,
            text_color=MishpitColors.TEXT_PRIMARY,
            height=80,
            corner_radius=8,
            command=self.show_card_input_withdraw
        )
        withdraw_btn.pack(padx=20, pady=20, fill="x")
        
        # Button: Deposit
        deposit_btn = ctk.CTkButton(
            self.main_frame,
            text="💰 Geld auf Karte laden",
            font=("Courier New", 18, "bold"),
            fg_color=MishpitColors.ACCENT,
            hover_color=MishpitColors.ACCENT_LIGHT,
            text_color=MishpitColors.TEXT_PRIMARY,
            height=80,
            corner_radius=8,
            command=self.show_deposit_amount_selection
        )
        deposit_btn.pack(padx=20, pady=20, fill="x")
        
        # Footer info
        footer = ctk.CTkLabel(
            self.main_frame,
            text="🔗 Verbunden mit: mishpit.com/MishBank\n1€ = 100 💾 (MishTokens)",
            font=("Courier New", 10),
            text_color=MishpitColors.TEXT_SECONDARY
        )
        footer.pack(pady=30)
    
    # ═════════════════════════════════════════════════════════════════════
    # FLOW: WITHDRAW – Step 1 (Card Input)
    # ═════════════════════════════════════════════════════════════════════
    
    def show_card_input_withdraw(self) -> None:
        """Step 1: Enter card number"""
        self.clear_frame()
        
        # Header
        header = ctk.CTkLabel(
            self.main_frame,
            text="💳 Kartennummer eingeben",
            font=("Courier New", 20, "bold"),
            text_color=MishpitColors.ACCENT
        )
        header.pack(pady=20)
        
        # Card input field
        card_var = tk.StringVar()
        card_entry = ctk.CTkEntry(
            self.main_frame,
            textvariable=card_var,
            font=("Courier New", 16),
            fg_color=MishpitColors.SECONDARY_BG,
            text_color=MishpitColors.TEXT_PRIMARY,
            border_color=MishpitColors.ACCENT,
            border_width=2,
            placeholder_text="Kartennummer (16 Ziffern)",
            height=50
        )
        card_entry.pack(padx=20, pady=20, fill="x")
        
        # Numeric keypad
        self._create_numeric_keypad(self.main_frame, card_var, max_length=16)
        
        # Continue button
        def on_continue():
            card_number = card_var.get()
            if len(card_number) != 16:
                self._show_error("❌ Bitte geben Sie eine gültige 16-stellige Kartennummer ein")
                return
            
            # Verify card with API
            print(f"🔍 Verifying card: {card_number}")
            response = MishBankAPI.verify_card(card_number)
            
            if response.get("success"):
                self.current_card = card_number
                self.show_withdrawal_amount_selection()
            else:
                self._show_error(response.get("message", "Karte nicht erkannt"))
        
        continue_btn = ctk.CTkButton(
            self.main_frame,
            text="✓ Weiter",
            font=("Courier New", 14, "bold"),
            fg_color=MishpitColors.SUCCESS,
            hover_color=MishpitColors.ACCENT_LIGHT,
            height=50,
            command=on_continue
        )
        continue_btn.pack(padx=20, pady=20, fill="x")
        
        # Back button
        back_btn = ctk.CTkButton(
            self.main_frame,
            text="← Zurück",
            font=("Courier New", 12),
            fg_color=MishpitColors.SECONDARY_BG,
            hover_color=MishpitColors.BORDER,
            text_color=MishpitColors.TEXT_SECONDARY,
            height=40,
            command=self.show_home_screen
        )
        back_btn.pack(padx=20, pady=10, fill="x")
    
    # ═════════════════════════════════════════════════════════════════════
    # FLOW: WITHDRAW – Step 2 (Amount Selection)
    # ═════════════════════════════════════════════════════════════════════
    
    def show_withdrawal_amount_selection(self) -> None:
        """Step 2: Select withdrawal amount"""
        self.clear_frame()
        
        # Header
        header = ctk.CTkLabel(
            self.main_frame,
            text="💰 Abhebungsbetrag",
            font=("Courier New", 20, "bold"),
            text_color=MishpitColors.ACCENT
        )
        header.pack(pady=20)
        
        # Amount options (in EUR)
        amounts_eur = [5, 10, 20, 50]
        
        for amt_eur in amounts_eur:
            amt_tokens = eur_to_tokens(amt_eur)
            tokens_str, eur_str = format_currency(amt_tokens)
            
            btn = ctk.CTkButton(
                self.main_frame,
                text=f"{tokens_str}\n{eur_str}",
                font=("Courier New", 14, "bold"),
                fg_color=MishpitColors.ACCENT,
                hover_color=MishpitColors.ACCENT_LIGHT,
                height=70,
                command=lambda amt=amt_tokens: self._confirm_withdrawal(amt)
            )
            btn.pack(padx=20, pady=10, fill="x")
        
        # Back button
        back_btn = ctk.CTkButton(
            self.main_frame,
            text="← Zurück",
            font=("Courier New", 12),
            fg_color=MishpitColors.SECONDARY_BG,
            hover_color=MishpitColors.BORDER,
            text_color=MishpitColors.TEXT_SECONDARY,
            height=40,
            command=self.show_home_screen
        )
        back_btn.pack(padx=20, pady=20, fill="x")
    
    def _confirm_withdrawal(self, amount_tokens: float) -> None:
        """Step 3: Confirm withdrawal amount"""
        self.withdrawal_amount = amount_tokens
        self.show_card_insertion_message()
    
    # ═════════════════════════════════════════════════════════════════════
    # FLOW: WITHDRAW – Step 3 (Card Insertion Message)
    # ═════════════════════════════════════════════════════════════════════
    
    def show_card_insertion_message(self) -> None:
        """Step 3: Message to insert card and enter PIN"""
        self.clear_frame()
        
        msg_box = ctk.CTkFrame(
            self.main_frame,
            fg_color=MishpitColors.SECONDARY_BG,
            border_color=MishpitColors.ACCENT,
            border_width=2,
            corner_radius=8
        )
        msg_box.pack(padx=20, pady=40, fill="both", expand=True)
        
        icon = ctk.CTkLabel(msg_box, text="💳", font=("Courier New", 60))
        icon.pack(pady=20)
        
        message = ctk.CTkLabel(
            msg_box,
            text="Karte einlegen und\nPIN auf dem Bedienfeld eingeben",
            font=("Courier New", 16, "bold"),
            text_color=MishpitColors.TEXT_PRIMARY,
            justify="center"
        )
        message.pack(pady=20)
        
        tokens_str, eur_str = format_currency(self.withdrawal_amount)
        amount_label = ctk.CTkLabel(
            msg_box,
            text=f"Betrag: {tokens_str}\n({eur_str})",
            font=("Courier New", 14),
            text_color=MishpitColors.ACCENT
        )
        amount_label.pack(pady=20)
        
        ok_btn = ctk.CTkButton(
            msg_box,
            text="✓ OK",
            font=("Courier New", 14, "bold"),
            fg_color=MishpitColors.SUCCESS,
            hover_color=MishpitColors.ACCENT_LIGHT,
            height=50,
            command=self.show_pin_input_withdraw
        )
        ok_btn.pack(padx=20, pady=20, fill="x")
    
    # ═════════════════════════════════════════════════════════════════════
    # FLOW: WITHDRAW – Step 4 (PIN Input)
    # ═════════════════════════════════════════════════════════════════════
    
    def show_pin_input_withdraw(self) -> None:
        """Step 4: Enter PIN via on-screen keypad"""
        self.clear_frame()
        
        header = ctk.CTkLabel(
            self.main_frame,
            text="🔐 PIN eingeben",
            font=("Courier New", 20, "bold"),
            text_color=MishpitColors.ACCENT
        )
        header.pack(pady=20)
        
        pin_var = tk.StringVar()
        pin_entry = ctk.CTkEntry(
            self.main_frame,
            textvariable=pin_var,
            font=("Courier New", 20),
            fg_color=MishpitColors.SECONDARY_BG,
            text_color=MishpitColors.ACCENT_BRIGHT,
            border_color=MishpitColors.ACCENT,
            border_width=2,
            placeholder_text="••••",
            show="•",
            height=50
        )
        pin_entry.pack(padx=20, pady=20, fill="x")
        
        self._create_numeric_keypad(self.main_frame, pin_var, max_length=4)
        
        def on_submit():
            pin = pin_var.get()
            if len(pin) != 4:
                self._show_error("❌ Bitte geben Sie eine 4-stellige PIN ein")
                return
            
            self.current_pin = pin
            self.process_withdrawal()
        
        submit_btn = ctk.CTkButton(
            self.main_frame,
            text="✓ Bestätigen",
            font=("Courier New", 14, "bold"),
            fg_color=MishpitColors.SUCCESS,
            hover_color=MishpitColors.ACCENT_LIGHT,
            height=50,
            command=on_submit
        )
        submit_btn.pack(padx=20, pady=20, fill="x")
    
    # ═════════════════════════════════════════════════════════════════════
    # FLOW: WITHDRAW – Step 5 (Process Transaction via API)
    # ═════════════════════════════════════════════════════════════════════
    
    def process_withdrawal(self) -> None:
        """Step 5: Verify PIN and process withdrawal"""
        print(f"🔐 Authenticating PIN for card: {self.current_card}")
        response = MishBankAPI.authenticate_pin(self.current_card, self.current_pin)
        
        if not response.get("success"):
            self._show_error(response.get("message", "PIN falsch"))
            self.show_home_screen()
            return
        
        # PIN correct - show animation
        self.show_withdrawal_animation()
    
    # ═════════════════════════════════════════════════════════════════════
    # FLOW: WITHDRAW – Step 6 (Animation & Servo Activation)
    # ═════════════════════════════════════════════════════════════════════
    
    def show_withdrawal_animation(self) -> None:
        """Step 6: Arrow animation + servo motor activation"""
        self.clear_frame()
        
        anim_box = ctk.CTkFrame(self.main_frame, fg_color=MishpitColors.BACKGROUND)
        anim_box.pack(fill="both", expand=True, padx=20, pady=40)
        
        arrow_label = ctk.CTkLabel(
            anim_box,
            text="↓",
            font=("Courier New", 80, "bold"),
            text_color=MishpitColors.ACCENT_BRIGHT
        )
        arrow_label.pack(pady=40)
        
        msg_label = ctk.CTkLabel(
            anim_box,
            text="Ihr Geld wird abgebucht\nTransaktion im Gange...",
            font=("Courier New", 14, "bold"),
            text_color=MishpitColors.TEXT_PRIMARY,
            justify="center"
        )
        msg_label.pack(pady=20)
        
        def animate():
            # Animate arrow (pulse effect)
            for _ in range(5):
                arrow_label.configure(text_color=MishpitColors.ACCENT_BRIGHT)
                time.sleep(0.3)
                arrow_label.configure(text_color=MishpitColors.ACCENT)
                time.sleep(0.3)
            
            # Trigger servo motor (cash dispensing)
            self.servo.dispense_cash()
            
            # Process withdrawal with API
            print(f"💸 Processing withdrawal: {self.withdrawal_amount} tokens")
            response = MishBankAPI.withdraw(self.current_card, self.withdrawal_amount)
            
            if response.get("success"):
                print(f"✅ Withdrawal successful! Transaction ID: {response.get('transaction_id')}")
                self.after(2000, self.show_withdrawal_success)
            else:
                print(f"❌ Withdrawal failed: {response.get('message')}")
                self.after(2000, lambda: self._show_error(response.get("message", "Fehler")))
        
        animation_thread = threading.Thread(target=animate, daemon=True)
        animation_thread.start()
    
    # ═════════════════════════════════════════════════════════════════════
    # FLOW: WITHDRAW – Step 7 (Success Screen)
    # ═════════════════════════════════════════════════════════════════════
    
    def show_withdrawal_success(self) -> None:
        """Step 7: Success screen with auto-reset"""
        self.clear_frame()
        
        success_box = ctk.CTkFrame(
            self.main_frame,
            fg_color=MishpitColors.SECONDARY_BG,
            border_color=MishpitColors.SUCCESS,
            border_width=2,
            corner_radius=8
        )
        success_box.pack(padx=20, pady=40, fill="both", expand=True)
        
        icon = ctk.CTkLabel(success_box, text="✅", font=("Courier New", 80))
        icon.pack(pady=20)
        
        message = ctk.CTkLabel(
            success_box,
            text="Danke für ihre Transaktion\nüber MishBank",
            font=("Courier New", 16, "bold"),
            text_color=MishpitColors.SUCCESS,
            justify="center"
        )
        message.pack(pady=20)
        
        timer_label = ctk.CTkLabel(
            success_box,
            text="Zurück zum Startbildschirm in 5 Sekunden...",
            font=("Courier New", 10),
            text_color=MishpitColors.TEXT_SECONDARY
        )
        timer_label.pack(pady=20)
        
        def reset():
            self.show_home_screen()
        
        self.after(5000, reset)
    
    # ═════════════════════════════════════════════════════════════════════
    # FLOW: DEPOSIT – Step 1 (Amount Selection) ← FIXED!
    # ═════════════════════════════════════════════════════════════════════
    
    def show_deposit_amount_selection(self) -> None:
        """Step 1: Select deposit amount (FIXED with predefined options)"""
        self.clear_frame()
        
        # Header
        header = ctk.CTkLabel(
            self.main_frame,
            text="💰 Einzahlungsbetrag",
            font=("Courier New", 20, "bold"),
            text_color=MishpitColors.ACCENT
        )
        header.pack(pady=20)
        
        # Amount options (in EUR) - SAME AS WITHDRAW
        amounts_eur = [5, 10, 20, 50]
        
        for amt_eur in amounts_eur:
            amt_tokens = eur_to_tokens(amt_eur)
            tokens_str, eur_str = format_currency(amt_tokens)
            
            btn = ctk.CTkButton(
                self.main_frame,
                text=f"{tokens_str}\n{eur_str}",
                font=("Courier New", 14, "bold"),
                fg_color=MishpitColors.ACCENT,
                hover_color=MishpitColors.ACCENT_LIGHT,
                height=70,
                command=lambda amt=amt_tokens: self._confirm_deposit(amt)
            )
            btn.pack(padx=20, pady=10, fill="x")
        
        # Back button
        back_btn = ctk.CTkButton(
            self.main_frame,
            text="← Zurück",
            font=("Courier New", 12),
            fg_color=MishpitColors.SECONDARY_BG,
            hover_color=MishpitColors.BORDER,
            text_color=MishpitColors.TEXT_SECONDARY,
            height=40,
            command=self.show_home_screen
        )
        back_btn.pack(padx=20, pady=20, fill="x")
    
    def _confirm_deposit(self, amount_tokens: float) -> None:
        """Step 2: Confirm deposit amount"""
        self.deposit_amount = amount_tokens
        self.show_deposit_confirmation()
    
    # ═════════════════════════════════════════════════════════════════════
    # FLOW: DEPOSIT – Step 2-5
    # ═════════════════════════════════════════════════════════════════════
    
    def show_deposit_confirmation(self) -> None:
        """Step 2: Confirm amount"""
        self.clear_frame()
        
        conf_box = ctk.CTkFrame(
            self.main_frame,
            fg_color=MishpitColors.SECONDARY_BG,
            border_color=MishpitColors.ACCENT,
            border_width=2,
            corner_radius=8
        )
        conf_box.pack(padx=20, pady=40, fill="both", expand=True)
        
        msg = ctk.CTkLabel(
            conf_box,
            text="Geld einlegen",
            font=("Courier New", 18, "bold"),
            text_color=MishpitColors.TEXT_PRIMARY
        )
        msg.pack(pady=20)
        
        tokens_str, eur_str = format_currency(self.deposit_amount)
        amount_label = ctk.CTkLabel(
            conf_box,
            text=f"{tokens_str}\n({eur_str})",
            font=("Courier New", 16, "bold"),
            text_color=MishpitColors.ACCENT_BRIGHT
        )
        amount_label.pack(pady=20)
        
        continue_btn = ctk.CTkButton(
            conf_box,
            text="✓ Weiter",
            font=("Courier New", 14, "bold"),
            fg_color=MishpitColors.SUCCESS,
            hover_color=MishpitColors.ACCENT_LIGHT,
            height=50,
            command=self.show_deposit_card_insertion
        )
        continue_btn.pack(padx=20, pady=20, fill="x")
    
    def show_deposit_card_insertion(self) -> None:
        """Step 3: Insert card"""
        self.clear_frame()
        
        msg_box = ctk.CTkFrame(
            self.main_frame,
            fg_color=MishpitColors.SECONDARY_BG,
            border_color=MishpitColors.ACCENT,
            border_width=2,
            corner_radius=8
        )
        msg_box.pack(padx=20, pady=40, fill="both", expand=True)
        
        message = ctk.CTkLabel(
            msg_box,
            text="Karte durchziehen",
            font=("Courier New", 18, "bold"),
            text_color=MishpitColors.TEXT_PRIMARY
        )
        message.pack(pady=20)
        
        card_icon = ctk.CTkLabel(
            msg_box,
            text="→ 💳 →",
            font=("Courier New", 40, "bold"),
            text_color=MishpitColors.ACCENT_BRIGHT
        )
        card_icon.pack(pady=20)
        
        continue_btn = ctk.CTkButton(
            msg_box,
            text="✓ Weiter",
            font=("Courier New", 14, "bold"),
            fg_color=MishpitColors.SUCCESS,
            hover_color=MishpitColors.ACCENT_LIGHT,
            height=50,
            command=self.show_deposit_card_input
        )
        continue_btn.pack(padx=20, pady=20, fill="x")
    
    def show_deposit_card_input(self) -> None:
        """Step 4: Enter card number"""
        self.clear_frame()
        
        header = ctk.CTkLabel(
            self.main_frame,
            text="💳 Kartennummer eingeben",
            font=("Courier New", 20, "bold"),
            text_color=MishpitColors.ACCENT
        )
        header.pack(pady=20)
        
        card_var = tk.StringVar()
        card_entry = ctk.CTkEntry(
            self.main_frame,
            textvariable=card_var,
            font=("Courier New", 16),
            fg_color=MishpitColors.SECONDARY_BG,
            text_color=MishpitColors.TEXT_PRIMARY,
            border_color=MishpitColors.ACCENT,
            border_width=2,
            placeholder_text="Kartennummer (16 Ziffern)",
            height=50
        )
        card_entry.pack(padx=20, pady=20, fill="x")
        
        self._create_numeric_keypad(self.main_frame, card_var, max_length=16)
        
        def on_continue():
            card_number = card_var.get()
            if len(card_number) != 16:
                self._show_error("❌ Bitte geben Sie eine gültige 16-stellige Kartennummer ein")
                return
            
            response = MishBankAPI.verify_card(card_number)
            if response.get("success"):
                self.current_card = card_number
                self.show_deposit_pin_input()
            else:
                self._show_error(response.get("message", "Karte nicht erkannt"))
        
        continue_btn = ctk.CTkButton(
            self.main_frame,
            text="✓ Weiter",
            font=("Courier New", 14, "bold"),
            fg_color=MishpitColors.SUCCESS,
            hover_color=MishpitColors.ACCENT_LIGHT,
            height=50,
            command=on_continue
        )
        continue_btn.pack(padx=20, pady=20, fill="x")
    
    def show_deposit_pin_input(self) -> None:
        """Step 5: Enter PIN"""
        self.clear_frame()
        
        header = ctk.CTkLabel(
            self.main_frame,
            text="🔐 PIN eingeben",
            font=("Courier New", 20, "bold"),
            text_color=MishpitColors.ACCENT
        )
        header.pack(pady=20)
        
        pin_var = tk.StringVar()
        pin_entry = ctk.CTkEntry(
            self.main_frame,
            textvariable=pin_var,
            font=("Courier New", 20),
            fg_color=MishpitColors.SECONDARY_BG,
            text_color=MishpitColors.ACCENT_BRIGHT,
            border_color=MishpitColors.ACCENT,
            border_width=2,
            placeholder_text="••••",
            show="•",
            height=50
        )
        pin_entry.pack(padx=20, pady=20, fill="x")
        
        self._create_numeric_keypad(self.main_frame, pin_var, max_length=4)
        
        def on_submit():
            pin = pin_var.get()
            if len(pin) != 4:
                self._show_error("❌ Bitte geben Sie eine 4-stellige PIN ein")
                return
            
            self.current_pin = pin
            self.process_deposit()
        
        submit_btn = ctk.CTkButton(
            self.main_frame,
            text="✓ Bestätigen",
            font=("Courier New", 14, "bold"),
            fg_color=MishpitColors.SUCCESS,
            hover_color=MishpitColors.ACCENT_LIGHT,
            height=50,
            command=on_submit
        )
        submit_btn.pack(padx=20, pady=20, fill="x")
    
    def process_deposit(self) -> None:
        """Step 6: Process deposit via API"""
        response = MishBankAPI.authenticate_pin(self.current_card, self.current_pin)
        
        if not response.get("success"):
            self._show_error(response.get("message", "PIN falsch"))
            self.show_home_screen()
            return
        
        # Process deposit with API
        print(f"💰 Processing deposit: {self.deposit_amount} tokens")
        response = MishBankAPI.deposit(self.current_card, self.deposit_amount)
        
        if response.get("success"):
            print(f"✅ Deposit successful! Transaction ID: {response.get('transaction_id')}")
            self.show_deposit_success()
        else:
            self._show_error(response.get("message", "Fehler"))
            self.show_home_screen()
    
    def show_deposit_success(self) -> None:
        """Step 7: Deposit success screen"""
        self.clear_frame()
        
        success_box = ctk.CTkFrame(
            self.main_frame,
            fg_color=MishpitColors.SECONDARY_BG,
            border_color=MishpitColors.SUCCESS,
            border_width=2,
            corner_radius=8
        )
        success_box.pack(padx=20, pady=40, fill="both", expand=True)
        
        icon = ctk.CTkLabel(success_box, text="✅", font=("Courier New", 80))
        icon.pack(pady=20)
        
        message = ctk.CTkLabel(
            success_box,
            text="Danke für ihre Einzahlung\nüber MishBank",
            font=("Courier New", 16, "bold"),
            text_color=MishpitColors.SUCCESS,
            justify="center"
        )
        message.pack(pady=20)
        
        tokens_str, eur_str = format_currency(self.deposit_amount)
        amount_label = ctk.CTkLabel(
            success_box,
            text=f"Eingezahlt: {tokens_str}\n({eur_str})",
            font=("Courier New", 14),
            text_color=MishpitColors.ACCENT
        )
        amount_label.pack(pady=20)
        
        timer_label = ctk.CTkLabel(
            success_box,
            text="Zurück zum Startbildschirm in 5 Sekunden...",
            font=("Courier New", 10),
            text_color=MishpitColors.TEXT_SECONDARY
        )
        timer_label.pack(pady=20)
        
        def reset():
            self.show_home_screen()
        
        self.after(5000, reset)
    
    # ═════════════════════════════════════════════════════════════════════
    # UTILITY: Numeric Keypad
    # ═════════════════════════════════════════════════════════════════════
    
    def _create_numeric_keypad(
        self,
        parent: ctk.CTkFrame,
        var: tk.StringVar,
        max_length: int = 16,
        allow_decimal: bool = False
    ) -> None:
        """Create numeric keypad"""
        keypad_frame = ctk.CTkFrame(parent, fg_color=MishpitColors.BACKGROUND)
        keypad_frame.pack(padx=20, pady=20, fill="both")
        
        buttons_layout = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["0", "←", "✓"] if not allow_decimal else ["0", ".", "←"]
        ]
        
        def add_digit(digit):
            current = var.get()
            if len(current) < max_length:
                var.set(current + digit)
        
        def backspace():
            current = var.get()
            var.set(current[:-1])
        
        for row in buttons_layout:
            row_frame = ctk.CTkFrame(keypad_frame, fg_color=MishpitColors.BACKGROUND)
            row_frame.pack(fill="x", pady=5)
            
            for btn_text in row:
                if btn_text == "←":
                    btn = ctk.CTkButton(
                        row_frame,
                        text=btn_text,
                        font=("Courier New", 14, "bold"),
                        fg_color=MishpitColors.ERROR,
                        hover_color="#cc5555",
                        width=60,
                        height=50,
                        command=backspace
                    )
                elif btn_text == "✓":
                    continue
                else:
                    btn = ctk.CTkButton(
                        row_frame,
                        text=btn_text,
                        font=("Courier New", 14, "bold"),
                        fg_color=MishpitColors.ACCENT,
                        hover_color=MishpitColors.ACCENT_LIGHT,
                        width=60,
                        height=50,
                        command=lambda d=btn_text: add_digit(d)
                    )
                
                btn.pack(side="left", padx=5, fill="both", expand=True)
    
    # ═════════════════════════════════════════════════════════════════════
    # UTILITY: Error Display
    # ═════════════════════════════════════════════════════════════════════
    
    def _show_error(self, message: str) -> None:
        """Display error message"""
        self.clear_frame()
        
        error_box = ctk.CTkFrame(
            self.main_frame,
            fg_color=MishpitColors.SECONDARY_BG,
            border_color=MishpitColors.ERROR,
            border_width=2,
            corner_radius=8
        )
        error_box.pack(padx=20, pady=40, fill="both", expand=True)
        
        icon = ctk.CTkLabel(error_box, text="❌", font=("Courier New", 60))
        icon.pack(pady=20)
        
        error_msg = ctk.CTkLabel(
            error_box,
            text=message,
            font=("Courier New", 14, "bold"),
            text_color=MishpitColors.ERROR,
            justify="center",
            wraplength=400
        )
        error_msg.pack(padx=20, pady=20)
        
        back_btn = ctk.CTkButton(
            error_box,
            text="← Zurück",
            font=("Courier New", 12, "bold"),
            fg_color=MishpitColors.SECONDARY_BG,
            hover_color=MishpitColors.BORDER,
            text_color=MishpitColors.TEXT_SECONDARY,
            height=40,
            command=self.show_home_screen
        )
        back_btn.pack(padx=20, pady=20, fill="x")
    
    # ═════════════════════════════════════════════════════════════════════
    # CLEANUP
    # ═════════════════════════════════════════════════════════════════════
    
    def on_closing(self):
        """Graceful shutdown"""
        print("\n🔌 Shutting down MishBank ATM...")
        self.servo.cleanup()
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Launch MishBank ATM"""
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                   🏦 MishBank ATM – Startup                              ║
║                     PRODUCTION VERSION - API LIVE                        ║
║                                                                          ║
║  Booting Mishpit-Style Banking System...                                ║
║  Raspberry Pi 5 + CustomTkinter + SG90 Servo                            ║
║                                                                          ║
║  🔗 API Endpoint: https://mishpit.com/MishBank/api.php                  ║
║  🌐 Status: Connected & Ready                                           ║
║                                                                          ║
║  Hardware: GPIO 17 (SG90 Servo) {Status: Available if on Pi}           ║
║                                                                          ║
║  Register a card at: https://mishpit.com/MishBank/                      ║
║  Then use the card number in this ATM!                                  ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    app = MishBankATM()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
