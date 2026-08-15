import type { MetadataRoute } from "next";
import { getDataIndex, listAllRaces } from "@/lib/data";
import { SITE_URL } from "@/lib/site";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const index = await getDataIndex();
  const races = await listAllRaces();
  const lastModified = new Date(index.updatedAt);

  return [
    { url: SITE_URL, lastModified, changeFrequency: "daily", priority: 1 },
    {
      url: `${SITE_URL}/results`,
      lastModified,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    { url: `${SITE_URL}/guide`, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE_URL}/about`, changeFrequency: "monthly", priority: 0.3 },
    ...index.meetDates.map((date) => ({
      url: `${SITE_URL}/races/${date}`,
      lastModified,
      changeFrequency: "daily" as const,
      priority: 0.9,
    })),
    ...races.map(({ date, track, raceNo }) => ({
      url: `${SITE_URL}/races/${date}/${track}/${raceNo}`,
      lastModified,
      changeFrequency: "daily" as const,
      priority: 0.7,
    })),
  ];
}
