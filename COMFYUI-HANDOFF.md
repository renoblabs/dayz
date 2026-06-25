# ComfyUI Cloud - Session Handoff

## Context

Working in the `dayz` monorepo. Goal: generate 6 sets of repository assets
using ComfyUI Cloud (SOTA models) and integrate them into the README.

## First thing to do

Check if comfyui-cloud MCP tools are available in this session:
- Look for comfyui tools in available MCP tools
- The MCP server is configured in `~/.claude.json` as:
  - type: http
  - url: https://cloud.comfy.org/mcp
  - X-API-Key already set

If tools are NOT loaded: tell the user - do not proceed with generation.
If tools ARE loaded: confirm and proceed to Asset 1.

## Aesthetic anchor (applies to ALL assets)

Industrial-military meets post-apocalyptic. Faded olive drab and rust orange.
Weathered metal, scratched surfaces, tactical readouts. NOT clean cyberpunk.
NOT glossy. The visual equivalent of a beat-up military laptop running real software.

Humour layer: self-aware, dry. "Lone operator with an unreasonable amount of
infrastructure." Think: the guy in the bunker with more dashboards than the
entire command center.

## Model selection

| Asset | Model |
|-------|-------|
| Hero banner (1280×320) | Flux 1.1 Pro |
| Footer (1280×200) | Flux 1.1 Pro |
| Logo/mark (512×512) | Flux Dev |
| Architecture diagram (1600×1200) | Flux Dev |
| Stream icons (4× 256×256) | SDXL or Flux Schnell |
| Dividers (3× 1200×80) | Flux Schnell |

## Generation order

1. Asset 1 - Hero banner (establishes visual anchor)
2. Asset 6 - Footer (same scene family, do while hero is fresh)
3. Asset 2 - Logo (pick Option A sigil or Option B stencil)
4. Asset 3 - Architecture diagram (different aesthetic, standalone)
5. Asset 4 - Stream icons (all 4 in same session for consistency)
6. Asset 5 - Dividers (quick filler, high volume)

## Save outputs to

```
~/Downloads/dayz-graphics/
|-- hero-banner.png
|-- logo-sigil.png (or logo-stencil.png)
|-- architecture-diagram.png
|-- stream-platform.png
|-- stream-hive.png
|-- stream-bosssignal.png
|-- stream-play.png
|-- divider-1.png
|-- divider-2.png
|-- divider-3.png
`-- status-footer.png
```

## After generation is done

Write a global Claude Code skill at `~/.claude/skills/comfyui-cloud.md` that captures
the working pattern for reuse across other repos. This was explicitly requested.

---

## Asset briefs

### Asset 1: Hero Banner (1280×320)

Concept: Wide tactical readout / command terminal in a survivor's makeshift ops room.
Multiple monitors showing data (graphs, server lists, mod stack tables - illegible but
plausible). Green CRT glow, amber emergency light. Room has been lived in.
NO human in frame. Empty chair - operator just stepped away.

**Prompt:**
```
ultra wide cinematic shot, abandoned command center in a post-apocalyptic survivor bunker,
multiple CRT monitors and tactical displays showing data dashboards graphs server lists,
green phosphor terminal glow, amber warning light, weathered olive drab military equipment,
rust patina on metal surfaces, scratched concrete walls, exposed conduit and cables,
makeshift desk built from ammo crates, beat-up mechanical keyboard, half-empty coffee mug,
scattered handwritten notes, tactical vest hanging on chair, empty operator chair,
moody atmospheric lighting, volumetric fog, dust particles in light beams,
shallow depth of field, photorealistic, gritty, lived-in, cinematic color grading,
subtle film grain, 35mm anamorphic lens look
```

**Negative:**
```
clean, polished, glossy, glamorous, modern office, bright lighting, sterile,
new equipment, pristine, futuristic sci-fi, cyberpunk neon, anime, illustration,
cartoon, low quality, blurry, oversaturated, people, person, character, face,
text overlay, watermark, logo
```

Params: Steps 40-50, CFG 4-5 (Flux), Euler sampler. Generate 4-6 variations.
Post-gen: add subtle stencil text overlay manually (e.g. `OPERATOR: 1` or `STATUS: HOLDING POSITION`).

---

### Asset 2: Logo / Mark (512×512)

Two options - recommend Option A (sigil).

**Option A - Sigil prompt:**
```
military unit patch design, embroidered fabric texture, circular shield shape,
faded olive drab and rust orange thread, central design featuring stylized
network architecture diagram with connected nodes integrated with subtle
hazard skull silhouette, distressed and weathered, frayed edges,
veteran's earned patch aesthetic, photorealistic embroidery detail,
isolated on transparent or dark background, centered composition,
flat lighting to emphasize texture
```

**Option B - Stencil prompt:**
```
military stencil spray painted text reading "DAYZ" on weathered shipping
container metal surface, cracked olive drab paint, rust streaks,
tactical military aesthetic, single bold stencil typography,
slash mark through text or tactical numbering below,
distressed and weathered, photorealistic close-up,
centered composition, harsh side lighting emphasizing texture
```

**Negative (both):**
```
clean, polished, modern logo design, vector art, flat design,
corporate, glossy, gradient, multiple subjects, watermark
```

Params: Steps 40-60, generate 6-8 variations.

---

### Asset 3: Architecture Diagram (1600×1200)

Concept: Hand-drawn technical schematic on aged graph paper. Five layers stacked.
Battlefield engineer's notebook. Coffee stains, fingerprints, eraser marks.

**Prompt:**
```
hand-drawn technical schematic on aged graph paper, military engineer's
field notebook page, five-layer architectural diagram drawn in cross-section,
sepia and blueprint blue ink, handwritten annotations in military stencil
font, layer 1 labeled "KNOWLEDGE BASE" drawn as data vault filing cabinet
with drawers, layer 2 labeled "INTEL" drawn as radio antenna array intercepting
signals, layer 3 labeled "CONFIG" drawn as wrench crossed with blueprint scroll,
layer 4 labeled "TOOLS" drawn as tactical handheld instruments, layer 5 labeled
"PLAY" drawn as small infantry foot patrol icon, connecting arrows and dotted
lines between layers, coffee stain in corner, eraser smudges, fingerprints,
graph paper grid visible underneath, weathered and aged, photorealistic
notebook texture, slight perspective tilt as if photographed on a desk
```

**Negative:**
```
clean digital design, vector graphics, modern UI, flat design,
sterile, bright colors, neon, cyberpunk, sci-fi, animated,
clean lines without texture, multiple pages, watermark
```

Note: AI text will hallucinate. Generate WITHOUT specific text labels,
then composite real labels in GIMP/Photoshop after. Much more reliable.
Params: Steps 40-60, generate 4-6.

---

### Asset 4: Stream Icons (4× 256×256)

Generate all 4 in the same session with identical settings for visual consistency.
Same model, same seed range, same CFG.

**Prompt template (replace [SUBJECT]):**
```
single bold stencil spray painted icon of [SUBJECT], military tactical
aesthetic, olive drab paint on weathered concrete wall background,
distressed and cracked paint, slight rust streaks, photorealistic
close-up texture, isolated centered subject, harsh directional lighting,
no text, no labels, single color silhouette
```

Subjects:
1. `multi-tool swiss army knife silhouette` - Platform stream
2. `geometric beehive hexagon pattern` - Hive stream
3. `radio antenna tower with signal pulse rings` - BossSignal stream
4. `tactical compass with crosshair` - Play stream

**Negative:**
```
detailed illustration, photorealistic object, color photo, multiple subjects,
text, labels, clean modern design, vector graphic
```

Params: 512×512, steps 30-40, generate 4-6 per icon. USE SAME SETTINGS FOR ALL 4.

---

### Asset 5: Section Dividers (3× 1200×80)

**Prompt:**
```
narrow horizontal tactical HUD readout strip, dark background,
amber and olive drab coordinate ticks and crosshair markings,
range indicator marks, subtle scan line, military targeting overlay,
minimalist, photorealistic CRT screen aesthetic, slight scanline
distortion, atmospheric, cinematic
```

**Negative:**
```
illustration, cartoon, clean modern UI, bright colors, multiple lines,
text, busy composition, watermark
```

Params: 1536×96 native (downscale to 1200×80). Steps 25-35. Generate 6-8, pick 3.

---

### Asset 6: Status Footer (1280×200)

Same bunker as hero banner, but exterior view. Dusk. Looking in through window/aperture.
Green CRT glow visible inside. Empty foreground. "The operator continues his work" mood.

**Prompt:**
```
ultra wide cinematic shot, exterior view of post-apocalyptic survivor bunker
at dusk, single window aperture glowing with green CRT terminal light from
inside, empty rust-stained concrete wall, faded military stencil markings
visible nearby, dust haze in foreground, dramatic sunset color grading,
purples and oranges in sky, atmospheric, lonely, cinematic, photorealistic,
shallow depth of field, 35mm anamorphic lens, subtle film grain
```

**Negative:**
```
people visible, character, face, bright daytime, clean modern building,
sci-fi, cyberpunk, multiple buildings, busy composition, text
```

Params: Same model/sampler as hero banner for consistency. Generate 4-6.
