# Visual and animation decisions

## Preserve the user's character

Start from the reference, not a generic cartoon template. Write a short identity specification and keep it across all frames. If the user wants the original appearance, preserve its face, proportions, hair, outfit, palette and instrument; do not add a new silhouette. Optional outfits/accessories require the user's brief. A small 180–310 px render must still be recognizable.

If a character sheet is requested, use one large signature pose, small front and side full bodies, and three head expressions on a clean warm-white board. That board is a design preview, not the runtime asset: the actual desktop pet needs separate transparent PNGs without labels or layout panels.

## Why guitar animation often fails

| Failure | Cause | Repair |
|---|---|---|
| Guitar swings or melts | Every frame redraws or rotates the whole character | Keep guitar, torso, head and feet fixed; isolate the playing arm |
| Fingers stretch | The hand is included in a nonrigid warp | Keep the hand shape rigid; deform the forearm smoothly |
| Hand floats away from wrist | Only the hand rotates | Include the complete arm and keep the shoulder anchored |
| Hand passes behind strings oddly | Incorrect layer order or excessive movement | Guitar below the playing arm, modest sweep across strings |
| Headphones slide between frames | Each frame generates new accessories | Use one fitted overlay if the head is stationary |
| Loop jumps | Last/first poses have different offsets | Sample one periodic cycle with consistent canvas coordinates |

For strumming, the fretting hand remains on the neck. The playing forearm moves gently around elbow/shoulder with a smaller wrist motion across the sound hole, perpendicular to the string direction. Use roughly 8–12 frames, a sine-like cycle and a modest amplitude. Derive joint positions from the actual character; never reuse another image's arm mask, skin threshold or coordinates as universal anatomy. If the hands overlap the guitar, reconstruct any exposed guitar region before compositing motion.

Other motions need their own anchors: paws on the ground for breathing, fixed torso and articulated limbs for waving, or a centered hinge for an object opening. Prefer a small clean motion over whole-body wobbling. Use offline rendered frames so runtime scaling and music state changes cannot deform shapes.

## Asset contract

- `idle.png`: RGBA transparent square, recommended 384–1024 px; complete silhouette with margin. One resting pose.
- `playing.png`: RGBA horizontal strip, `N × side` wide and `side` high; N defaults to 8. Every frame uses the same scale and placement. Do not leave a white background.
- Optional `background`/`foreground`: one square or an N-frame horizontal strip of the same side. Runtime order is background → character → foreground. These overlays are hidden when idle.
- `fps`: frame advances per second, default 12 for 8 frames (1.5 loops/s). It is a visual loop; the music detector does not calculate beats or BPM.
- Transparent pixels must exist in each frame. Keep edges clean. Tk uses a Windows color key and thresholds alpha at 128, so this template is suitable for opaque outlined characters rather than smoke or softly translucent shadows.

## Headphones and musical curves

Fit a headband to the real head/hair contour. Place ear cups at the ears, maintain the face outline, and use restrained highlights/shadows for depth. Light cherry-blossom pink, gold trim and darker cushions were one user's chosen treatment; infer other users' colors from their brief.

Use thin colorful curves near the head with phase shifts and gentle amplitude. Keep the face readable and margin around the ears. Music curves are decorative, not measured audio spectrum. Generate them as independent paths/layers; don't distort the character to create liveliness.

## Review before installation

View the transparent image on both dark and light backgrounds, then a looping GIF at the actual desktop size. Check the first/last frame boundary, stationary props, wrist/shoulder connections, headset fit and scale180/310/620. If the user finds the motion wrong, fix the relevant joint/layer rather than adding another full-character rotation.
