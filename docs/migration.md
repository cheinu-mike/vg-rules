# Updates and switching installers

## Back up first

Save a separate `.blend` copy and export your rules as JSON. Keep both backups until
you have verified the replacement. Import replaces the current list; it does not merge.

## Replace an installation

1. Disable and remove the existing VG Rules through Preferences. When moving from
   Gumroad to the extension, remove the legacy add-on before enabling the extension.
2. Install the replacement ZIP following [installation](installation.md).
3. Save Preferences if automatic saving is disabled.
4. **Fully quit Blender and start it again before Preview or Apply.** Blender can
   retain old modules after reinstalling; restarting is required to load updated code.
5. Open the saved `.blend`, inspect the rules and targets, and Preview.
6. If rules need restoration, import your JSON backup, inspect targets and Preview
   again before Apply. Do not discard the original backups yet.

Use only one installation. The extension's module namespace differs from the legacy
add-on, while operator IDs, preset format and saved rule properties remain compatible.
Disable and remove the previous installation before enabling its replacement.
If enabling fails, check for duplicate installations, remove the duplicate and restart.

## Behavior introduced in 0.1.1

Imported names and executable targets now resolve only within the executing scene.
A saved pointer outside that scene remains saved and its rule is skipped. Link the
object into the intended scene or choose a local mesh. Do not expect another scene's
object to be chosen by a same-name fallback.

One object linked into several scenes now requires shared-data confirmation, even
when no second object shares its mesh. Review all affected scenes before Continue.
Preset exports are atomic and refuse installed VG Rules directories.

See [CHANGELOG](../CHANGELOG.md) for release history.

## Sidebar fix in 0.1.2

The published 0.1.2 fixes an empty panel caused by scene-property writes during
drawing in 0.1.1 by deferring initialization to a timer.
Use the restart procedure above when replacing 0.1.1.

## Saved rules in 0.1.3 and later development builds

The first release, 0.1.0, already saved separate Keep/Delete collections and
object-binding history. Files created with released versions need no rule-format
conversion. The current development source reads saved Scene properties directly
and uses property defaults for new scenes. Enabling VG Rules, loading a file and
drawing the sidebar do not initialize or validate rules and schedule no scene timer.

The sidebar displays each live target's current name without rewriting saved data.
Preview/Apply refresh binding metadata when the rule is used. Preset import and
export validate their data; Preview/Apply check targets and rule values before
planning mesh changes. These checks run for the requested operation, not on file load.

## Support

If an update or installer switch fails, reopen the saved copy and report through
[GitHub Issues](https://github.com/cheinu-mike/vg-rules/issues). Include both versions,
installer type and Results text. Use a synthetic reproduction instead of personal models.
