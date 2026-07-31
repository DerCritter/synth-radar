import asyncio
import logging
from synth_arbitrage.scraper import scrape_all_platforms

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def main():
    print("Iniciando prueba diagnóstica del scraper...")
    opportunities = await scrape_all_platforms()
    print(f"\n✅ Análisis completado. Se encontraron {len(opportunities)} oportunidades.")
    for o in opportunities[:10]:
        print(f"- {o.get('Modelo', 'Unknown')} | {o.get('Precio URL', 0)}€ | {o.get('Plataforma', 'N/A')} | {o.get('Ahorro %', '0%')}")
    if len(opportunities) > 10:
        print(f"... y {len(opportunities) - 10} más.")

if __name__ == "__main__":
    asyncio.run(main())
