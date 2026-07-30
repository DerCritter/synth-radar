"""Backward compatibility shim for Supabase client interface.

Re-exports SupabaseDB from the synth_arbitrage.database submodule.
"""

from synth_arbitrage.database import SupabaseDB

__all__ = ["SupabaseDB"]
