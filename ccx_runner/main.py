import dearpygui.dearpygui as dpg
from ccx_runner.gui.hauptfenster import Hauptfenster

def main():
    # INIT GUI
    dpg.create_context()
    dpg.create_viewport(title='CalculiX Job Control', width=600, height=300)

    hauptfenster = Hauptfenster()
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window(hauptfenster.id, True)
    
    dpg.start_dearpygui()
    dpg.destroy_context()
