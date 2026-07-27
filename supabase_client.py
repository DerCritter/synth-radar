import os
import logging
from supabase import create_client, Client

class SupabaseDB:
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_KEY")
        if not self.url or not self.key:
            logging.warning("SUPABASE_URL or SUPABASE_KEY not set. Supabase client won't work correctly.")
            self.client = None
        else:
            self.client = create_client(self.url, self.key)

    def _map_to_db(self, item):
        return {
            "url": item.get("Enlace"),
            "modelo": item.get("Modelo"),
            "estado": item.get("Estado"),
            "precio": item.get("Precio URL"),
            "precio_mercado": item.get("Precio Mercado"),
            "ahorro_porcentaje": item.get("Ahorro %"),
            "plataforma": item.get("Plataforma"),
            "imagen": item.get("Imagen"),
            "reverb": item.get("Reverb"),
            "mensaje_borrador": item.get("Mensaje Borrador"),
            "last_seen": item.get("last_seen"),
            "fecha_agregado": item.get("Fecha Agregado")
        }

    def _map_from_db(self, item):
        return {
            "Enlace": item.get("url"),
            "Modelo": item.get("modelo"),
            "Estado": item.get("estado"),
            "Precio URL": item.get("precio"),
            "Precio Mercado": item.get("precio_mercado"),
            "Ahorro %": item.get("ahorro_porcentaje"),
            "Plataforma": item.get("plataforma"),
            "Imagen": item.get("imagen"),
            "Reverb": item.get("reverb"),
            "Mensaje Borrador": item.get("mensaje_borrador"),
            "last_seen": item.get("last_seen"),
            "Fecha Agregado": item.get("fecha_agregado")
        }

    def upsert_listings(self, listings_list):
        if not self.client:
            return None
        
        if not listings_list:
            return []

        db_items = [self._map_to_db(item) for item in listings_list]
        try:
            # We assume 'url' is the primary key
            response = self.client.table("listings").upsert(db_items).execute()
            return response.data
        except Exception as e:
            logging.error(f"Error upserting listings to Supabase: {e}")
            return None

    def get_listings(self):
        if not self.client:
            return []
        
        try:
            response = self.client.table("listings").select("*").execute()
            return [self._map_from_db(item) for item in response.data]
        except Exception as e:
            logging.error(f"Error getting listings from Supabase: {e}")
            return []
