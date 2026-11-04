// Scales an ImageBitmap down off the main thread (D91): createImageBitmap with a resize runs
// synchronously on the thread that calls it (~40 ms for a 2048 texture), so models.ts sends it here.

interface Job {
  id: number;
  bitmap: ImageBitmap;
  width: number;
  height: number;
}

self.onmessage = async (e: MessageEvent<Job>) => {
  const { id, bitmap, width, height } = e.data;
  try {
    const out = await createImageBitmap(bitmap, { resizeWidth: width, resizeHeight: height, resizeQuality: "high", premultiplyAlpha: "none", colorSpaceConversion: "none" });
    bitmap.close();
    (self as unknown as Worker).postMessage({ id, bitmap: out }, [out]);
  } catch {
    // Not scaled: the original goes back, so the texture still has its image.
    (self as unknown as Worker).postMessage({ id, bitmap }, [bitmap]);
  }
};
