"""Database interface module for SynthRadar arbitrage system.

Provides Supabase client wrapper and dictionary mapping operations between
in-memory opportunity representations and Supabase relational schema.
"""

import logging
import os
from typing import Any, Dict, List, Optional

try:
    from supabase import Client, create_client
except ImportError:
    Client = Any  # type: ignore
    create_client = None  # type: ignore


class SupabaseDB:
    """Supabase client wrapper for persisting and querying gear listings."""

    def __init__(self) -> None:
        """Initializes Supabase connection using environment variables."""
        self.url: Optional[str] = os.environ.get("SUPABASE_URL")
        self.key: Optional[str] = os.environ.get("SUPABASE_KEY")
        if not self.url or not self.key or create_client is None:
            logging.warning("SUPABASE_URL or SUPABASE_KEY not set (or supabase module missing). Supabase client won't work correctly.")
            self.client: Optional[Client] = None
        else:
            self.client = create_client(self.url, self.key)

    def _map_to_db(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Maps in-memory opportunity item dictionary to Supabase DB column fields.

        Args:
            item: Opportunity dictionary with user-facing keys.

        Returns:
            Dict containing database column keys and values.
        """
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
            "fecha_agregado": item.get("Fecha Agregado"),
        }

    def _map_from_db(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Maps database column row dictionary to user-facing opportunity fields.

        Args:
            item: Database row dict from Supabase.

        Returns:
            Dict containing user-facing opportunity keys.
        """
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
            "Fecha Agregado": item.get("fecha_agregado"),
        }

    def upsert_listings(self, listings_list: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """Upserts a list of listing opportunities into Supabase database.

        Args:
            listings_list: List of opportunity dictionaries to persist.

        Returns:
            List of upserted database record dicts if successful, empty list if input empty,
            or None if client is unavailable or write operation fails.
        """
        if not self.client:
            return None

        if not listings_list:
            return []

        db_items = [self._map_to_db(item) for item in listings_list]
        try:
            response = self.client.table("listings").upsert(db_items).execute()
            return response.data
        except Exception as e:
            logging.error(f"Error upserting listings to Supabase: {e}")
            return None

    def get_listings(self) -> List[Dict[str, Any]]:
        """Retrieves all listing opportunities stored in Supabase database.

        Returns:
            List of mapped user-facing listing dictionaries, or empty list on failure.
        """
        if not self.client:
            return []

        try:
            response = self.client.table("listings").select("*").execute()
            return [self._map_from_db(item) for item in response.data]
        except Exception as e:
            logging.error(f"Error getting listings from Supabase: {e}")
            return []
