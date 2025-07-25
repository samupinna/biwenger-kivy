from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

class MainScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)

        self.add_widget(Label(text='BIWENGER MANAGER', font_size=32))

        btn1 = Button(text='Procesar jornada (Excel)', size_hint=(1, 0.2))
        btn1.bind(on_press=self.procesar_jornada)
        self.add_widget(btn1)

        btn2 = Button(text='Ver clasificación', size_hint=(1, 0.2))
        btn2.bind(on_press=self.ver_clasificacion)
        self.add_widget(btn2)

        self.status = Label(text='', size_hint=(1, 0.2))
        self.add_widget(self.status)

    def procesar_jornada(self, instance):
        self.status.text = "Funcionalidad aún no implementada."

    def ver_clasificacion(self, instance):
        self.status.text = "Funcionalidad aún no implementada."

class BiwengerApp(App):
    def build(self):
        return MainScreen()

if __name__ == "__main__":
    BiwengerApp().run()
