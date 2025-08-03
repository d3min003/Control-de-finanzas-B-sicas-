import sys
import sqlite3
import csv
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QDateEdit, QMessageBox, QHeaderView, QGroupBox, QFormLayout,
    QDoubleSpinBox, QProgressBar, QFrame, QListWidget,
    QListWidgetItem, QDialog, QDialogButtonBox, QMenu,
    QAbstractItemView, QStyleFactory, QInputDialog
)
from PyQt5.QtCore import Qt, QDate, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor, QPixmap, QIcon, QPainter, QImage
from PyQt5.QtChart import QChart, QChartView, QPieSeries, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis

# ====================== BASE DE DATOS SIMPLIFICADA ======================
class DatabaseManager:
    def __init__(self, db_name='finanzas.db'):
        self.connection = sqlite3.connect(db_name)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.connection.cursor()
        
        # Tabla de usuarios
        cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY,
                        nombre TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        moneda TEXT DEFAULT '$')''')
        
        # Tabla de ingresos
        cursor.execute('''CREATE TABLE IF NOT EXISTS ingresos (
                        id INTEGER PRIMARY KEY,
                        usuario_id INTEGER NOT NULL,
                        tipo TEXT NOT NULL,
                        monto REAL NOT NULL,
                        fecha DATE NOT NULL,
                        descripcion TEXT)''')
        
        # Tabla de gastos
        cursor.execute('''CREATE TABLE IF NOT EXISTS gastos (
                        id INTEGER PRIMARY KEY,
                        usuario_id INTEGER NOT NULL,
                        categoria TEXT NOT NULL,
                        tipo TEXT NOT NULL,
                        monto REAL NOT NULL,
                        fecha DATE NOT NULL,
                        descripcion TEXT)''')
        
        # Tabla de deudas
        cursor.execute('''CREATE TABLE IF NOT EXISTS deudas (
                        id INTEGER PRIMARY KEY,
                        usuario_id INTEGER NOT NULL,
                        nombre TEXT NOT NULL,
                        tipo TEXT NOT NULL,
                        monto_inicial REAL NOT NULL,
                        monto_actual REAL NOT NULL,
                        tasa_interes REAL,
                        fecha_inicio DATE,
                        fecha_pago DATE)''')
        
        # Tabla de objetivos
        cursor.execute('''CREATE TABLE IF NOT EXISTS objetivos (
                        id INTEGER PRIMARY KEY,
                        usuario_id INTEGER NOT NULL,
                        titulo TEXT NOT NULL,
                        tipo TEXT NOT NULL,
                        monto_actual REAL DEFAULT 0,
                        meta REAL,
                        fecha_creacion DATE,
                        fecha_meta DATE,
                        completado BOOLEAN DEFAULT 0)''')
        
        # Tabla de notificaciones
        cursor.execute('''CREATE TABLE IF NOT EXISTS notificaciones (
                        id INTEGER PRIMARY KEY,
                        usuario_id INTEGER NOT NULL,
                        titulo TEXT NOT NULL,
                        mensaje TEXT NOT NULL,
                        fecha DATE NOT NULL,
                        leida BOOLEAN DEFAULT 0)''')
        
        self.connection.commit()
    
    def execute_query(self, query, params=None):
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        self.connection.commit()
        return cursor
    
    def fetch_all(self, query, params=None):
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()
    
    def fetch_one(self, query, params=None):
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchone()
    
    def close(self):
        self.connection.close()

# ====================== COMPONENTES UI ======================
class CardWidget(QFrame):
    def __init__(self, title, value, color, icon=None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumWidth(200)
        self.setStyleSheet(f"""
            #card {{
                background: #ffffff;
                border-radius: 12px;
                padding: 15px;
                border: 1px solid #e0e0e0;
            }}
            QLabel#card-title {{
                font-size: 14px;
                color: #6c757d;
                font-weight: 500;
            }}
            QLabel#card-value {{
                font-size: 24px;
                font-weight: 700;
                margin-top: 8px;
            }}
        """)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        lbl_title = QLabel(title)
        lbl_title.setObjectName("card-title")
        layout.addWidget(lbl_title)
        
        self.lbl_value = QLabel(value)
        self.lbl_value.setObjectName("card-value")
        self.lbl_value.setStyleSheet(f"color: {color};")
        layout.addWidget(self.lbl_value)

    def setValue(self, value):
        self.lbl_value.setText(value)

class ModernButton(QPushButton):
    def __init__(self, text, color="#0d6efd", parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(36)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {self.adjust_color(color, 20)};
            }}
        """)
    
    def adjust_color(self, hex_color, amount):
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        r = min(255, max(0, r + amount))
        g = min(255, max(0, g + amount))
        b = min(255, max(0, b + amount))
        return f"#{r:02x}{g:02x}{b:02x}"

class GoalWidget(QWidget):
    def __init__(self, title, goal_type, current, target, currency="$", parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            background-color: #ffffff;
            border-radius: 8px;
            padding: 12px;
            border: 1px solid #e0e0e0;
        """)
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        # Información del objetivo
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Arial", 11, QFont.Bold))
        info_layout.addWidget(lbl_title)
        
        lbl_type = QLabel(f"Tipo: {goal_type}")
        lbl_type.setFont(QFont("Arial", 9))
        lbl_type.setStyleSheet("color: #6c757d;")
        info_layout.addWidget(lbl_type)
        
        # Barra de progreso
        progress = (current / target) * 100 if target > 0 else 0
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(int(progress))
        self.progress_bar.setFormat(f"{currency}{current:,.2f} de {currency}{target:,.2f} ({progress:.0f}%)")
        self.progress_bar.setStyleSheet('''
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                text-align: center;
                height: 20px;
                background: #f8f9fa;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #20c997;
                border-radius: 6px;
            }
        ''')
        info_layout.addWidget(self.progress_bar)
        
        layout.addLayout(info_layout, 1)
        
        # Botón para completar
        self.btn_complete = ModernButton("✓", color="#20c997")
        self.btn_complete.setFixedSize(32, 32)
        self.btn_complete.setToolTip("Marcar como completado")
        layout.addWidget(self.btn_complete)

# ====================== PESTAÑA DASHBOARD ======================
class DashboardTab(QWidget):
    def __init__(self, db_manager, user_id):
        super().__init__()
        self.db_manager = db_manager
        self.user_id = user_id
        self.currency = "$"
        self.init_ui()
        self.refresh_data()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 15, 20, 20)
        self.setLayout(main_layout)
        
        # Encabezado
        header_layout = QHBoxLayout()
        title = QLabel("Resumen Financiero")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        header_layout.addWidget(title)
        
        # Botón de actualizar
        self.refresh_btn = ModernButton("Actualizar", color="#0d6efd")
        self.refresh_btn.setFixedWidth(100)
        self.refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.refresh_btn)
        
        main_layout.addLayout(header_layout)
        
        # Tarjetas de resumen
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        
        # Crear tarjetas
        self.income_card = CardWidget("Ingresos Totales", f"{self.currency}0", "#0d6efd")
        self.expense_card = CardWidget("Gastos Totales", f"{self.currency}0", "#dc3545")
        self.savings_card = CardWidget("Ahorros", f"{self.currency}0", "#20c997")
        self.net_card = CardWidget("Patrimonio Neto", f"{self.currency}0", "#6f42c1")
        
        cards_layout.addWidget(self.income_card)
        cards_layout.addWidget(self.expense_card)
        cards_layout.addWidget(self.savings_card)
        cards_layout.addWidget(self.net_card)
        
        main_layout.addLayout(cards_layout)
        
        # Gráficos
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(15)
        
        # Gráfico de gastos por categoría
        self.expense_chart = self.create_expense_chart()
        chart_frame = QFrame()
        chart_frame.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e0e0e0;")
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.addWidget(QLabel("Distribución de Gastos"))
        chart_layout.addWidget(self.expense_chart)
        charts_layout.addWidget(chart_frame, 1)
        
        # Gráfico de ingresos vs gastos
        self.income_vs_expense_chart = self.create_income_vs_expense_chart()
        chart_frame2 = QFrame()
        chart_frame2.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e0e0e0;")
        chart_layout2 = QVBoxLayout(chart_frame2)
        chart_layout2.addWidget(QLabel("Ingresos vs Gastos (Últimos 6 meses)"))
        chart_layout2.addWidget(self.income_vs_expense_chart)
        charts_layout.addWidget(chart_frame2, 1)
        
        main_layout.addLayout(charts_layout)
        
        # Objetivos
        goals_group = QGroupBox("Objetivos Financieros")
        goals_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                margin-top: 0;
                padding-top: 20px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                font-weight: bold;
            }
        """)
        goals_layout = QVBoxLayout()
        goals_group.setLayout(goals_layout)
        
        self.goals_list = QListWidget()
        self.goals_list.setStyleSheet("background-color: #ffffff; border: none;")
        self.goals_list.setMinimumHeight(150)
        
        goals_layout.addWidget(self.goals_list)
        main_layout.addWidget(goals_group)
    
    def create_expense_chart(self):
        self.pie_series = QPieSeries()
        self.chart = QChart()
        self.chart.addSeries(self.pie_series)
        self.chart.setTitle("")
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignRight)
        
        chart_view = QChartView(self.chart)
        chart_view.setMinimumHeight(250)
        return chart_view
    
    def create_income_vs_expense_chart(self):
        self.set_income = QBarSet("Ingresos")
        self.set_expense = QBarSet("Gastos")
        
        self.bar_series = QBarSeries()
        self.bar_series.append(self.set_income)
        self.bar_series.append(self.set_expense)
        
        self.bar_chart = QChart()
        self.bar_chart.addSeries(self.bar_series)
        self.bar_chart.setTitle("")
        
        # Ejes
        months = [QDate.currentDate().addMonths(-i).toString("MMM") for i in range(5, -1, -1)]
        self.axis_x = QBarCategoryAxis()
        self.axis_x.append(months)
        self.bar_chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.bar_series.attachAxis(self.axis_x)
        
        self.axis_y = QValueAxis()
        self.axis_y.setLabelFormat(f"{self.currency}%d")
        self.bar_chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.bar_series.attachAxis(self.axis_y)
        
        chart_view = QChartView(self.bar_chart)
        chart_view.setMinimumHeight(250)
        return chart_view
    
    def refresh_data(self):
        # Actualizar tarjetas
        total_income = self.db_manager.fetch_one(
            "SELECT SUM(monto) FROM ingresos WHERE usuario_id = ?", (self.user_id,)
        )[0] or 0
        
        total_expense = self.db_manager.fetch_one(
            "SELECT SUM(monto) FROM gastos WHERE usuario_id = ?", (self.user_id,)
        )[0] or 0
        
        total_savings = self.db_manager.fetch_one(
            "SELECT SUM(monto_actual) FROM objetivos WHERE usuario_id = ?", (self.user_id,)
        )[0] or 0
        
        total_debts = self.db_manager.fetch_one(
            "SELECT SUM(monto_actual) FROM deudas WHERE usuario_id = ?", (self.user_id,)
        )[0] or 0
        
        net_worth = total_savings - total_debts
        
        self.income_card.setValue(f"{self.currency}{total_income:,.2f}")
        self.expense_card.setValue(f"{self.currency}{total_expense:,.2f}")
        self.savings_card.setValue(f"{self.currency}{total_savings:,.2f}")
        self.net_card.setValue(f"{self.currency}{net_worth:,.2f}")
        
        # Actualizar gráfico de gastos
        self.pie_series.clear()
        expense_data = self.db_manager.fetch_all(
            "SELECT categoria, SUM(monto) FROM gastos WHERE usuario_id = ? GROUP BY categoria",
            (self.user_id,)
        )
        
        colors = ["#dc3545", "#fd7e14", "#ffc107", "#20c997", "#0d6efd", "#6f42c1"]
        for i, (category, amount) in enumerate(expense_data):
            if amount > 0:
                slice_ = self.pie_series.append(category, amount)
                slice_.setColor(QColor(colors[i % len(colors)]))
        
        # Actualizar gráfico de barras
        self.set_income.remove(0, self.set_income.count())
        self.set_expense.remove(0, self.set_expense.count())
        
        current_date = QDate.currentDate()
        for i in range(6):
            month_start = current_date.addMonths(-i).addDays(-current_date.day() + 1)
            month_end = month_start.addMonths(1).addDays(-1)
            
            monthly_income = self.db_manager.fetch_one(
                "SELECT SUM(monto) FROM ingresos WHERE usuario_id = ? AND fecha BETWEEN ? AND ?",
                (self.user_id, month_start.toString("yyyy-MM-dd"), month_end.toString("yyyy-MM-dd"))
            )[0] or 0
            
            monthly_expense = self.db_manager.fetch_one(
                "SELECT SUM(monto) FROM gastos WHERE usuario_id = ? AND fecha BETWEEN ? AND ?",
                (self.user_id, month_start.toString("yyyy-MM-dd"), month_end.toString("yyyy-MM-dd"))
            )[0] or 0
            
            self.set_income.append(monthly_income)
            self.set_expense.append(monthly_expense)
        
        # Actualizar lista de objetivos
        self.goals_list.clear()
        goals = self.db_manager.fetch_all(
            "SELECT id, titulo, tipo, monto_actual, meta FROM objetivos WHERE usuario_id = ? AND completado = 0",
            (self.user_id,)
        )
        
        for goal_id, title, goal_type, current, target in goals:
            item = QListWidgetItem()
            widget = GoalWidget(title, goal_type, current, target, self.currency)
            widget.btn_complete.clicked.connect(
                lambda _, gid=goal_id: self.mark_goal_completed(gid))
            item.setSizeHint(widget.sizeHint())
            self.goals_list.addItem(item)
            self.goals_list.setItemWidget(item, widget)
    
    def mark_goal_completed(self, goal_id):
        self.db_manager.execute_query(
            "UPDATE objetivos SET completado = 1 WHERE id = ?", (goal_id,)
        )
        self.refresh_data()

# ====================== PESTAÑA INGRESOS ======================
class IncomeTab(QWidget):
    def __init__(self, db_manager, user_id):
        super().__init__()
        self.db_manager = db_manager
        self.user_id = user_id
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 15, 20, 20)
        self.setLayout(main_layout)
        
        # Formulario
        form_layout = QFormLayout()
        
        # Tipo de ingreso
        self.income_type = QComboBox()
        self.income_type.addItems(["Sueldo", "Freelance", "Inversiones", "Regalías", "Otros"])
        
        # Monto
        self.income_amount = QDoubleSpinBox()
        self.income_amount.setRange(0, 1000000)
        self.income_amount.setPrefix("$ ")
        
        # Fecha
        self.income_date = QDateEdit()
        self.income_date.setDate(QDate.currentDate())
        self.income_date.setCalendarPopup(True)
        
        # Descripción
        self.income_description = QLineEdit()
        
        form_layout.addRow("Tipo:", self.income_type)
        form_layout.addRow("Monto:", self.income_amount)
        form_layout.addRow("Fecha:", self.income_date)
        form_layout.addRow("Descripción:", self.income_description)
        
        # Botón
        btn_add = ModernButton("Agregar Ingreso", color="#0d6efd")
        btn_add.clicked.connect(self.add_income)
        form_layout.addRow(btn_add)
        
        main_layout.addLayout(form_layout)
        
        # Tabla de ingresos
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Tipo", "Monto", "Fecha", "Descripción"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet('''
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
            }
        ''')
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        main_layout.addWidget(self.table)
    
    def add_income(self):
        self.db_manager.execute_query(
            "INSERT INTO ingresos (usuario_id, tipo, monto, fecha, descripcion) VALUES (?, ?, ?, ?, ?)",
            (self.user_id,
             self.income_type.currentText(),
             self.income_amount.value(),
             self.income_date.date().toString("yyyy-MM-dd"),
             self.income_description.text())
        )
        self.load_data()
        self.income_description.clear()
        self.income_amount.setValue(0)
    
    def load_data(self):
        data = self.db_manager.fetch_all(
            "SELECT id, tipo, monto, fecha, descripcion FROM ingresos WHERE usuario_id = ? ORDER BY fecha DESC",
            (self.user_id,)
        )
        self.table.setRowCount(len(data))
        
        for row, record in enumerate(data):
            for col, value in enumerate(record):
                item = QTableWidgetItem(str(value))
                if col == 2:  # Monto
                    item.setText(f"${float(value):,.2f}")
                self.table.setItem(row, col, item)
    
    def show_context_menu(self, pos):
        menu = QMenu()
        delete_action = menu.addAction("Eliminar")
        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        
        if action == delete_action:
            selected_row = self.table.currentRow()
            if selected_row >= 0:
                income_id = self.table.item(selected_row, 0).text()
                self.db_manager.execute_query("DELETE FROM ingresos WHERE id = ?", (income_id,))
                self.load_data()

# ====================== PESTAÑA GASTOS ======================
class ExpensesTab(QWidget):
    def __init__(self, db_manager, user_id):
        super().__init__()
        self.db_manager = db_manager
        self.user_id = user_id
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 15, 20, 20)
        self.setLayout(main_layout)
        
        # Formulario
        form_layout = QFormLayout()
        
        # Categoría
        self.expense_category = QComboBox()
        self.expense_category.addItems([
            "Vivienda", "Alimentación", "Transporte", "Entretenimiento", 
            "Salud", "Educación", "Otros"
        ])
        
        # Monto
        self.expense_amount = QDoubleSpinBox()
        self.expense_amount.setRange(0, 1000000)
        self.expense_amount.setPrefix("$ ")
        
        # Fecha
        self.expense_date = QDateEdit()
        self.expense_date.setDate(QDate.currentDate())
        self.expense_date.setCalendarPopup(True)
        
        # Descripción
        self.expense_description = QLineEdit()
        
        form_layout.addRow("Categoría:", self.expense_category)
        form_layout.addRow("Monto:", self.expense_amount)
        form_layout.addRow("Fecha:", self.expense_date)
        form_layout.addRow("Descripción:", self.expense_description)
        
        # Botón
        btn_add = ModernButton("Agregar Gasto", color="#dc3545")
        btn_add.clicked.connect(self.add_expense)
        form_layout.addRow(btn_add)
        
        main_layout.addLayout(form_layout)
        
        # Tabla de gastos
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Categoría", "Monto", "Fecha", "Descripción"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet('''
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
            }
        ''')
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        main_layout.addWidget(self.table)
    
    def add_expense(self):
        self.db_manager.execute_query(
            "INSERT INTO gastos (usuario_id, categoria, tipo, monto, fecha, descripcion) VALUES (?, ?, ?, ?, ?, ?)",
            (self.user_id,
             self.expense_category.currentText(),
             "Variable",  # Tipo fijo para simplificar
             self.expense_amount.value(),
             self.expense_date.date().toString("yyyy-MM-dd"),
             self.expense_description.text())
        )
        self.load_data()
        self.expense_description.clear()
        self.expense_amount.setValue(0)
    
    def load_data(self):
        data = self.db_manager.fetch_all(
            "SELECT id, categoria, monto, fecha, descripcion FROM gastos WHERE usuario_id = ? ORDER BY fecha DESC",
            (self.user_id,)
        )
        self.table.setRowCount(len(data))
        
        for row, record in enumerate(data):
            for col, value in enumerate(record):
                item = QTableWidgetItem(str(value))
                if col == 2:  # Monto
                    item.setText(f"${float(value):,.2f}")
                    item.setForeground(QColor("#dc3545"))
                self.table.setItem(row, col, item)
    
    def show_context_menu(self, pos):
        menu = QMenu()
        delete_action = menu.addAction("Eliminar")
        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        
        if action == delete_action:
            selected_row = self.table.currentRow()
            if selected_row >= 0:
                expense_id = self.table.item(selected_row, 0).text()
                self.db_manager.execute_query("DELETE FROM gastos WHERE id = ?", (expense_id,))
                self.load_data()

# ====================== PESTAÑA AHORROS ======================
class SavingsTab(QWidget):
    def __init__(self, db_manager, user_id):
        super().__init__()
        self.db_manager = db_manager
        self.user_id = user_id
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 15, 20, 20)
        self.setLayout(main_layout)
        
        # Formulario
        form_layout = QFormLayout()
        
        # Título
        self.goal_title = QLineEdit()
        
        # Tipo
        self.goal_type = QComboBox()
        self.goal_type.addItems(["Emergencia", "Vacaciones", "Educación", "Retiro", "Otro"])
        
        # Montos
        self.goal_current = QDoubleSpinBox()
        self.goal_current.setPrefix("$ ")
        self.goal_target = QDoubleSpinBox()
        self.goal_target.setPrefix("$ ")
        
        # Fecha meta
        self.goal_date = QDateEdit()
        self.goal_date.setDate(QDate.currentDate().addMonths(6))
        self.goal_date.setCalendarPopup(True)
        
        form_layout.addRow("Título:", self.goal_title)
        form_layout.addRow("Tipo:", self.goal_type)
        form_layout.addRow("Monto actual:", self.goal_current)
        form_layout.addRow("Meta:", self.goal_target)
        form_layout.addRow("Fecha meta:", self.goal_date)
        
        # Botón
        btn_add = ModernButton("Agregar Objetivo", color="#20c997")
        btn_add.clicked.connect(self.add_savings)
        form_layout.addRow(btn_add)
        
        main_layout.addLayout(form_layout)
        
        # Tabla de ahorros
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Título", "Tipo", "Actual", "Meta", "Completado"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet('''
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
            }
        ''')
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        main_layout.addWidget(self.table)
    
    def add_savings(self):
        self.db_manager.execute_query(
            "INSERT INTO objetivos (usuario_id, titulo, tipo, monto_actual, meta, fecha_creacion, fecha_meta) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.user_id,
             self.goal_title.text(),
             self.goal_type.currentText(),
             self.goal_current.value(),
             self.goal_target.value(),
             QDate.currentDate().toString("yyyy-MM-dd"),
             self.goal_date.date().toString("yyyy-MM-dd"))
        )
        self.load_data()
        self.goal_title.clear()
        self.goal_current.setValue(0)
        self.goal_target.setValue(0)
    
    def load_data(self):
        data = self.db_manager.fetch_all(
            "SELECT id, titulo, tipo, monto_actual, meta, completado FROM objetivos WHERE usuario_id = ?",
            (self.user_id,)
        )
        self.table.setRowCount(len(data))
        
        for row, record in enumerate(data):
            for col, value in enumerate(record):
                item = QTableWidgetItem(str(value))
                if col in [3, 4]:  # Montos
                    item.setText(f"${float(value):,.2f}")
                elif col == 5:  # Completado
                    item.setText("Sí" if value == 1 else "No")
                    item.setForeground(QColor("#20c997" if value == 1 else "#dc3545"))
                self.table.setItem(row, col, item)
    
    def show_context_menu(self, pos):
        menu = QMenu()
        delete_action = menu.addAction("Eliminar")
        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        
        if action == delete_action:
            selected_row = self.table.currentRow()
            if selected_row >= 0:
                goal_id = self.table.item(selected_row, 0).text()
                self.db_manager.execute_query("DELETE FROM objetivos WHERE id = ?", (goal_id,))
                self.load_data()

# ====================== APLICACIÓN PRINCIPAL ======================
class FinancialDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión Financiera Personal")
        self.setGeometry(100, 100, 1200, 800)
        self.user_id = 1  # ID de usuario fijo para simplificar
        
        # Configurar base de datos
        self.db_manager = DatabaseManager()
        self.create_sample_data()
        
        # Crear pestañas
        self.tabs = QTabWidget()
        
        self.dashboard_tab = DashboardTab(self.db_manager, self.user_id)
        self.income_tab = IncomeTab(self.db_manager, self.user_id)
        self.expenses_tab = ExpensesTab(self.db_manager, self.user_id)
        self.savings_tab = SavingsTab(self.db_manager, self.user_id)
        
        self.tabs.addTab(self.dashboard_tab, "🏠 Dashboard")
        self.tabs.addTab(self.income_tab, "📊 Ingresos")
        self.tabs.addTab(self.expenses_tab, "💸 Gastos")
        self.tabs.addTab(self.savings_tab, "💰 Ahorros")
        
        # Configurar layout principal
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        main_widget.setLayout(main_layout)
        
        self.setCentralWidget(main_widget)
    
    def create_sample_data(self):
        # Crear usuario por defecto
        self.db_manager.execute_query(
            "INSERT OR IGNORE INTO usuarios (id, nombre, email) VALUES (?, ?, ?)",
            (self.user_id, "Usuario Demo", "demo@finanzas.com")
        )
        
        # Crear datos de muestra si la base está vacía
        income_count = self.db_manager.fetch_one(
            "SELECT COUNT(*) FROM ingresos WHERE usuario_id = ?", (self.user_id,)
        )[0] or 0
        
        if income_count == 0:
            today = datetime.now().date()
            
            # Ingresos de muestra
            self.db_manager.execute_query(
                "INSERT INTO ingresos (usuario_id, tipo, monto, fecha, descripcion) VALUES (?, ?, ?, ?, ?)",
                (self.user_id, "Sueldo", 2500.00, today.strftime("%Y-%m-%d"), "Salario mensual")
            )
            
            # Gastos de muestra
            self.db_manager.execute_query(
                "INSERT INTO gastos (usuario_id, categoria, tipo, monto, fecha, descripcion) VALUES (?, ?, ?, ?, ?, ?)",
                (self.user_id, "Vivienda", "Fijo", 800.00, today.strftime("%Y-%m-%d"), "Alquiler")
            )
            
            # Objetivos de muestra
            self.db_manager.execute_query(
                "INSERT INTO objetivos (usuario_id, titulo, tipo, monto_actual, meta, fecha_creacion, fecha_meta) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (self.user_id, "Fondo Emergencia", "Emergencia", 500.00, 5000.00, 
                 today.strftime("%Y-%m-%d"), (today + timedelta(days=180)).strftime("%Y-%m-%d"))
            )

# ====================== EJECUCIÓN ======================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    window = FinancialDashboard()
    window.show()
    sys.exit(app.exec_())