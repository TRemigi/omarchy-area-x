# omarchy-area-x

The shell plugin for the [Annihilation theme](https://github.com/TRemigi/omarchy-annihilation-theme)
for [Omarchy](https://omarchy.org/): *Area X*, the Shimmer and what grows in it. A Quickshell plugin
(id `annihilation.shimmer`) with a service and a bar widget. It does nothing unless the `annihilation`
theme is the active one, so it is safe to leave installed when you switch themes.

## Install

    omarchy plugin add https://github.com/TRemigi/omarchy-area-x.git --enable
    omarchy restart shell

and to update it:

    omarchy plugin update annihilation.shimmer
    omarchy restart shell

An update only re-scans plugins; a release that adds a QML file or a shader needs the restart. The
theme itself is a separate repo, and the Hyprland tweaks and the hook that turns off Omarchy's own
screensaver (which this plugin's screensaver waits for) are part of its `extras/install link`.
If you ran that before this plugin had its own repo, it left a symlink at
`~/.config/omarchy/plugins/annihilation.shimmer`; delete that link (`rm ~/.config/omarchy/plugins/annihilation.shimmer`,
not `omarchy plugin remove`, which switches the plugin off in `shell.json` first) and then add this one. Your
settings and the bar glyph's place stay: they are keyed by the plugin id, which has not changed.

Plugins run as unsandboxed code inside `omarchy-shell`; read before you enable.

## What it does

| Part | What it does |
| --- | --- |
| Shimmer layer | A click-through layer between wallpaper and windows, modelled on how the film shows it: the air seems to bend light. A translucent film of spectral colour (teal, blue, violet, magenta, pink, orange) drifts over the whole scene, its colour flowing and swirling into other colour and shifting the hue of whatever is behind it while keeping its detail, with the occasional faint curtain of light and warm glows drifting in from the edges. Its strength and colour vary from place to place and from moment to moment, nothing is scripted, and every session is different. Pauses under fullscreen windows. |
| Window glow | Light spilling over the edges of your windows, as if it came from behind them. Two fans of prism light enter from beyond the screen edges and wander slowly around them; a window edge lights up where a fan's light reaches it, in a soft blended band a few dozen pixels deep that dissolves smoothly inward and follows the window's real corner radius, with a faint halo just outside and a few soft bright glints drifting along the edges. In cursor mode only the active window glows, faintly, and the part of its edge nearest your pointer pools the light, spilling in outward from the pointer when it takes over from another edge. It lives in a click-through layer above the windows, hides under fullscreen windows, and follows windows as they open, close, move and change workspace (an interactive resize catches up when you let go). |
| Screensaver | After `idle.screensaver` seconds the wallpaper slowly warps, its colour channels drift apart, and a fungus grows in from the edges of the screen, keeping to the background: pale root-like veins branching inward, and patches of olive mould with yellow spots gathering round them. A passage appears one part at a time in the middle of the screen, each fading in and out in turn, always starting from the first part. The words are alive: made of tiny hand-shaped creatures that wave their fingers and glow in slow swells, which now and then release a few spores from one point. Stands down while Omarchy's own screensaver is enabled, or while the bar's Stay Awake is on. |
| Notifications | A quiet synthesized tone when a notification arrives (on by default, silent for screenshot and recording toasts). Notifications that went by unnoticed (silenced by Do Not Disturb, or left on screen until they expired) leave one to three small motes on the bar prism and a list in its popup until you open it. All of it reads the notification service's own files, so it works with Omarchy's stock daemon. |
| Bar glyph | A prism whose edge shifts teal, magenta, amber. Click for "Day N inside Area X" (uptime), the day's log entry and the controls; right click toggles the layer; middle click starts the screensaver. |

### Settings

Fields on the plugin's entry in `~/.config/omarchy/shell.json` (the bar glyph's
entry under `bar.layout`, or `plugins[]` if you run it without the glyph):

| Field | Default | |
| --- | --- | --- |
| `layerEnabled` | `true` | the wallpaper layer |
| `layerIntensity` | `0.44` | 0 to 1 |
| `layerSpeed` | `1.29` | how fast the Shimmer evolves, 0.1 to 4 times its natural pace (the popup's slider covers 0.25 to 3) |
| `windowGlow` | `true` | the light on window edges; `false` turns just that off |
| `windowGlowSpan` | `1.98` | in cursor mode, how much length of edge the pool covers, 0.5 to 2.5 times the default (also a slider in the popup) |
| `windowGlowDepth` | `0.21` | how far into a window the glow reaches, 0.02 to 2.5 times the default (the popup slider starts at 0.05); the bright spot at the base of the cursor glow is a streak along the edge, as thick as the depth and as long as the span (also a slider in the popup) |
| `windowGlowCenter` | `0.98` | in cursor mode, the brightness of the glow's bright centre (its core and point), 0 to 2.5 times the default (the "Glow brightness" slider in the popup) |
| `windowGlowMode` | `"all"` | `"all"`: every window glows evenly. `"cursor"`: only the active window, faintly, with the span of its edge nearest the pointer wider and brighter (also a toggle in the bar popup) |
| `layerAdditive` | `true` | add the light to the wallpaper; `false` blends it as an ordinary translucent layer if your compositor mishandles that |
| `notifySound` | `true` | a soft tone when a notification arrives; not for Omarchy's own screenshot and recording toasts unless critical, at most one a second, never under the screensaver |
| `notifySoundVolume` | `0.5` | 0.05 to 1 |
| `motes` | `true` | the spores |
| `fpsCap` | `30` | 5 to 60 |
| `screensaver` | `true` | set `false` to keep Omarchy's idle behavior without it |
| `screensaverSeconds` | `0` | `0` follows `idle.screensaver`; it does not start on idle if this is not shorter than `idle.lock`, and it is off while the bar's Stay Awake is on, and while Omarchy's own screensaver is enabled (Toggle Screensaver in the menu) |
| `passageAlive` | `true` | the passage is grown from tiny hand-shaped creatures that wave and glow, and releases a few spores once a part; `false` is plain glowing text |
| `screensaverBrightness` | `0.08` | how much of the photo shows, 0.02 to 1 |
| `passageFont` | `"jost"` | `"jost"`, `"cinzel"`, or the name of any installed font |

The popup's "Reset to defaults" button removes the popup's own fields (the sliders and switches) from the entry, so the defaults above apply again. It leaves `windowGlow`, `layerAdditive`, `fpsCap` and the screensaver and passage fields alone.

### Commands

    omarchy-shell shimmer pulse          # a slow swell of intensity
    omarchy-shell shimmer toggleLayer
    omarchy-shell shimmer screensaver    # start it now; any key or click ends it
    omarchy-shell shimmer dismiss
    omarchy-shell shimmer status
    omarchy-shell shimmer notify 1       # pretend a notification arrived (0 low, 1 normal, 2 critical)
    omarchy-shell shimmer sound arrive   # hear a tone: arrive, low or urgent
    omarchy-shell shimmer seen           # mark missed notifications seen (the popup does this itself)


### The screensaver passage

`passage.txt` ships original text in the manner of the tower wall writing. To
spell out something else, such as the passage from the book, put it in
`~/.config/omarchy/annihilation-passage.txt`, one part per line. That file
replaces the shipped one and is picked up as soon as you save it. Lines too
long for the screen are broken at word boundaries, preferably after
punctuation, so a pasted paragraph still reads in turn.

### Fonts

The film's logotype is custom and no free font matches it exactly. The passage
is set in heavy capitals in Jost (a Futura-like geometric sans),
the nearest freely licensed look. `"cinzel"` gives classical Roman capitals
instead. Any other value is taken as the name of an installed font, so a
lookalike you install yourself, such as Kiona, works too. Jost and Cinzel are
bundled under the SIL Open Font License; the licences are in
`fonts/`.

### Editing the shaders

`shaders/*.frag` are compiled to the
committed `.qsb` files with `build-shaders.sh` (needs `qt6-shadertools`).
`journal.txt` holds the bar popup's daily entries, one per line.

## Working on it

Clone the repo and link it instead of adding it, so edits show up without a pull:

    ln -s ~/dev/omarchy-area-x ~/.config/omarchy/plugins/annihilation.shimmer
    omarchy-shell shell rescanPlugins          # after editing; the shell's watcher does not follow symlinks

`omarchy plugin validate .` checks the manifest (and rejects symlinks inside the plugin folder; the
link above is outside it). The logic tests and the shader harnesses are in `dev/`; `AGENTS.md` says how to
run them and why the design is the way it is.
