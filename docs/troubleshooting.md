# Troubleshooting VG Rules

| Symptom | What to check |
| --- | --- |
| No VG Rules tab | Enable the extension, open a 3D Viewport, press N and select VG Rules. Check that Blender is 4.2 or later. |
| Empty panel in 0.1.1 | Update to 0.1.2 and fully restart Blender. This fixes scene-property writes during sidebar drawing. |
| Installation or registration conflict | Disable/remove duplicate VG Rules installations, then fully restart Blender. Use one installer type at a time. |
| Object not found | Select a mesh in this scene. After clearing/deleting a bound target, reselect it or explicitly edit Fallback Name. |
| Outside-scene warning | The saved pointer is retained. Link that object into this scene or select a local mesh. |
| Edit Mode warning | Leave Edit Mode on the target and every object sharing its mesh. |
| Read-only target warning | Use an editable local object and mesh; linked library data may be read-only. |
| Shared-data confirmation | Inspect every named object and scene. Continue allows those shared effects; Cancel leaves the batch intact. |
| All blocked by duplicate/shared targets | Disable extra enabled rules or use Preview Rule / Apply Rule separately. Opting into shared data does not bypass batch conflicts. |
| Keep does not prevent a weight change | Keep prevents deletion only. Full Weights overwrites existing weights, including kept/locked groups. |
| Opposite Mirror group is empty | This is intended: Mirror Weights empties the opposite source group and enables modifier vertex-group mirroring. |
| Auto Side cannot decide | Choose Left or Right explicitly. Check matching bones or an X Mirror plane and avoid zero-scale reference transforms. |
| Regex error or timeout | Simplify patterns or use literal matching. Maximum 4096 characters/pattern, 64/section and one second of matching per rule. |
| Missing/failed regex worker | Use an official Blender distribution with bundled Python. Check that its interpreter is present/readable. No system Python or package installation is required. |
| Group name too long | Shorten it to 63 UTF-8 bytes including side suffix; non-ASCII characters may use multiple bytes. |
| Import rejected | Correct invalid or unsupported fields, blank rows, malformed names or regex. Previous settings are preserved on validation failure. |
| Export rejected | Pick a writable user folder outside installed VG Rules directories. Existing presets survive failed writes/replacement. |
| Update seems unchanged | Fully quit and restart Blender. Preview the saved rules after restart before Apply. |
| Need to recover changes | Use Undo in the current session or reopen the separate `.blend` copy. |

## Report a problem

Use [GitHub Issues](https://github.com/cheinu-mike/vg-rules/issues) as the support destination.
Include:

- OS, Blender version, VG Rules version and whether you installed the extension or legacy add-on.
- Exact reproduction steps and expected versus actual behavior.
- Results text, warning/error messages and a screenshot if helpful.
- A small synthetic mesh and preset if needed. Remove personal/confidential data first.

The full source and installed-extension suites, including read-only directories,
pass on Windows x64, Linux x64 and macOS Apple Silicon with Blender 4.2.0,
4.2.23 and 5.2.0, and macOS Intel with 4.2.0 and 4.2.23. Blender 5.2.0 on Intel
macOS is unsupported because there is no official build. Local GUI checks cover
Windows only. See [actual results and scope](../submission/COMPLIANCE.md).
