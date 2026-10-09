# Use VG Rules

## First rule

1. Save current work and start a fresh General scene. Select the Cube in Object Mode.
2. Open **VG Rules** in the 3D Viewport sidebar and click **Add Selected**.
3. Leave **Keep** and **Delete** empty. Under **Full Weights - All Vertices**, click **+**.
4. Enter `DemoWeight`, set **Side** to **Exact Name**, and leave **Mirror Weights** off.
5. Click **Preview Rule**. Results should show 0 deletions, 1 assignment and 0 warnings.
   Preview leaves groups and weights untouched.
6. Save a separate `.blend` copy and click **Apply Rule**. `DemoWeight` now has
   weight 1.0 on all eight Cube vertices.

Inspect groups under **Object Data Properties > Vertex Groups**. Use Undo in the
current session or reopen your saved copy to recover.

## Targets, lists and execution

**New Rule** adds an empty rule; **Add Selected** adds selected meshes without
duplicating existing targets. The picker and imported names resolve in the executing
scene. Outside-scene pointers remain saved but are skipped with a warning. Link the
object into the scene or select a local mesh. Editing **Fallback Name** explicitly
opts back into name resolution after a cleared/deleted target.

**Preview Rule / Apply Rule** run the selected rule, including a disabled rule chosen
explicitly. **Preview All / Apply All** use enabled rules only. All blocks duplicate
enabled targets and different enabled objects sharing a mesh. Disable extra rules
or run selected rules separately. Invalid rules may be skipped while valid rules run;
Results gives counts and warnings. Leave Edit Mode on all users of the target mesh.

## Keep and Delete

Each section supports **Exact, Prefix, Suffix, Contains and Regex**. Matching ignores
case unless that section's **Case Sensitive** box is enabled. Any Keep match protects
against every Delete filter. Keep by itself deletes nothing. Blank rows and invalid
patterns need correction or removal before that rule can run.

For a small cleanup example, keep prefix `DEF-` and exact name `cloth_pin`; delete
prefix `MCH-` and contained text `_backup`. Only explicit unprotected matches delete.

## Full Weights overwrites

Each assignment gives **every vertex weight 1.0**, including hidden and unselected
vertices. Missing groups are created. Existing assigned-group weights are replaced
even when the group is kept or weight-locked. Keep protects against deletion only.
The group lock flags themselves remain unchanged.

Final group names allow **63 UTF-8 bytes**, including `.L`/`.R`; a side-pair base
allows 61 bytes. Non-ASCII characters may occupy several bytes. Overlong names skip
the rule before cleanup.

## Side and Mirror

**Exact Name** uses the entered name. **Left / Right** resolves `.L`/`.R`. **Auto Side**
uses matching rest-pose bones or an existing X Mirror plane when matching bones are
unavailable. Ambiguous detection warns; choose a side explicitly.

**Mirror Weights** requires an existing Mirror modifier. It creates the opposite
source group if necessary and **empties all its weights**, including kept or locked
groups. It enables vertex-group mirroring on existing Mirror modifiers. It does not
apply the modifiers, copy arbitrary weights or create a complete rig.

## Shared data and scenes

Mesh changes can affect other users, including hidden objects, objects outside this
scene and unlinked objects. A single object linked into multiple scenes also affects
each scene. Preview and the Apply dialog list affected objects and their scenes.
**Continue** permits those effects; **Cancel** leaves the entire batch unchanged.

## Regex limits

Regex uses Python syntax and search semantics. Use `^`/`$` when you need anchors.
Limits are **4096 characters per pattern**, **64 patterns per Keep/Delete section**
and a **one-second matching worker deadline per rule**. The worker exclusively uses
Blender's bundled Python. Invalid, slow, missing or failed workers skip the affected
rule before mutation. Use simpler regex or literal filters; install no extra packages.

## Presets

Rules persist in the `.blend`. **Export** writes JSON atomically; failed writes
preserve an existing preset. Export cannot overwrite installed VG Rules files,
including disabled copies. Choose a writable user folder.

**Import replaces the rule list after validation**. Export a backup first. JSON and
Python files with a literal `OBJECT_RULES` dictionary are supported. Python code is
read as data and never executed. For moves and updates, follow [migration](migration.md).

For help, use [troubleshooting](troubleshooting.md) or
[GitHub Issues](https://github.com/cheinu-mike/vg-rules/issues).
