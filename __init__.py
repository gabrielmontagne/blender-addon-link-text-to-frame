import bpy
from bpy.types import Operator, Panel
from bpy.path import abspath
from functools import reduce
from bpy.props import StringProperty, BoolProperty, IntProperty
from subprocess import run
from shlex import split
from requests import post, get

bl_info = {
    'name': 'Link Text to Node Frame',
    'author': 'gabriel montagné, gabriel@tibas.london',
    'version': (1, 0, 0),
    'blender': (2, 80, 0),
    'description': 'Quickly link a new text object to a frame node',
    'tracker_url': 'https://github.com/gabrielmontagne/blender-addon-link-text-to-frame/issues'
}

MARGIN = 15

def find_linked(start):
    return reduce(linked_reroutes,[ start ], [])

def linked_reroutes(acc, start):
    result = acc + [ start ]
    to_nodes = [l.to_node for l in start.outputs[0].links if l.to_node]
    for n in to_nodes:
        result = reduce(linked_reroutes, to_nodes, result)
    return result

class NODE_OP_split_frame_from_lines(bpy.types.Operator):
    """Split frame from lines"""
    bl_idname = "node.split_frame_from_lines"
    bl_label = "Split frame from lines"

    unlink_texts: BoolProperty(name='Unlink texts', default=True)
    from_file: StringProperty(name='File')

    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, "from_file", bpy.data, 'texts')
        layout.prop(self, "unlink_texts")

    @classmethod
    def poll(cls, context):
        return context.area.type == 'NODE_EDITOR' and context.active_node and context.active_node.type == 'FRAME'

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        active_node = context.active_node
        w, h = active_node.dimensions

        lines = [l.body.strip() for l in bpy.data.texts[self.from_file].lines if l.body.strip()]
        assert len(lines), 'Should have at least one line'

        active_node.label= lines[0]

        for line in lines[1:]:
            bpy.ops.node.duplicate()
            bpy.ops.node.translate_attach(TRANSFORM_OT_translate={'value': (0, -(h + MARGIN), 0)})
            context.active_node.label = line
            if self.unlink_texts:
                context.active_node.text = None

        return {'FINISHED'}

class NODE_OP_relink_text(Operator):
    """Relink text from frame"""
    bl_idname = "node.relink_text_from_frame"
    bl_label = "Relink Text to Frame - a new one, even if present."

    raise_in_editor: BoolProperty(name='Raise in editor', default=True)

    @classmethod
    def poll(cls, context):
        return context.area.type == 'NODE_EDITOR' and context.active_node and context.active_node.type == 'FRAME'

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        active_node = bpy.context.active_node
        label = active_node.label or active_node.name

        text = bpy.data.texts.new(label)
        text.write('<+++>')
        active_node.text = text

        if self.raise_in_editor:
            for area in bpy.context.screen.areas:
                if area.type == 'TEXT_EDITOR':
                    area.spaces[0].text = text
                    break

        return {'FINISHED'}

class NODE_OP_unlink_text(Operator):
    """Unlink text from frame"""
    bl_idname = "node.unlink_text_from_frame"
    bl_label = "Unlink Text from Frame"

    @classmethod
    def poll(cls, context):
        return context.area.type == 'NODE_EDITOR' and context.active_node and context.active_node.type == 'FRAME'

    def execute(self, context):
        active_node = bpy.context.active_node
        active_node.text = None

        return {'FINISHED'}


class NODE_OP_link_text(Operator):
    """Link text to frame"""
    bl_idname = "node.link_text_to_frame"
    bl_label = "Link Text to Frame"

    raise_in_editor: BoolProperty(name='Raise in editor', default=True)

    @classmethod
    def poll(cls, context):
        return context.area.type == 'NODE_EDITOR' and context.active_node and context.active_node.type == 'FRAME'

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        active_node = bpy.context.active_node
        label = active_node.label or active_node.name
        text = active_node.text

        if not text:
            text = bpy.data.texts.new(label)
            text.write('<+++>')
            active_node.text = text

        if self.raise_in_editor:
            for area in bpy.context.screen.areas:
                if area.type == 'TEXT_EDITOR':
                    area.spaces[0].text = text
                    break

        return {'FINISHED'}

class NODE_OP_post_to_texere(Operator):
    """Post text to Téxere Sereno"""
    bl_idname = "node.post_text_to_texere"
    bl_label = "Post text to texere"

    server_port: IntProperty(description='Proccessing server port', default=3000)

    @classmethod
    def poll(cls, context):
        space = bpy.context.space_data
        try:
            filepath = space.text.name
            if filepath.strip() == "": return False
            return (space.type == 'TEXT_EDITOR')
        except AttributeError: return False

    def execute(self, context):
        space = context.space_data
        r = post(f'http://0.0.0.0:{self.server_port}/note', space.text.as_string().encode())
        if r.ok:
            return {'FINISHED'}
        self.report({'ERROR'}, f'Unable to connect to texere notes on port {self.server_port} - is it running?')
        return {'CANCELLED'}

class NODE_OP_get_from_texere(Operator):
    """Get text from Téxere Sereno"""
    bl_idname = "node.get_text_from_texere"
    bl_label = "Get text from texere"

    server_port: IntProperty(description='Proccessing server port', default=3000)

    @classmethod
    def poll(cls, context):
        space = bpy.context.space_data
        try:
            filepath = space.text.name
            if filepath.strip() == "": return False
            return (space.type == 'TEXT_EDITOR')
        except AttributeError: return False

    def execute(self, context):
        space = context.space_data
        r = get(f'http://0.0.0.0:{self.server_port}/note')

        if r.ok:
            text = space.text
            text.clear()
            text.write(r.text)
            return {'FINISHED'}

        self.report({'ERROR'}, f'Unable to connect to texere notes on port {self.server_port} - is it running?')
        return {'CANCELLED'}

class NODE_PT_texere_panel(Panel):
    """Controls for interacting with Texere Sereno"""
    bl_label = "Post to Téxere Sereno"
    bl_space_type = 'TEXT_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Text"

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator('node.post_text_to_texere')
        row = layout.row(align=True)
        row.operator('node.get_text_from_texere')

class NODE_OP_collate_text(Operator):
    """Collate linked texts"""

    bl_idname = "node.collate_linked_frames"
    bl_label = "Collate all linked texts"

    save_target: BoolProperty(name='Save target')
    target: StringProperty(name='To file')
    add_context_label: BoolProperty(name='Add context labels', default=True)
    shell_command: StringProperty(name='Command')
    shell_context: StringProperty(name='CWD', default='//', subtype='DIR_PATH')
    unfurl_to_vse: BoolProperty(name='Unfurl to VSE')
    set_range_to_strips: BoolProperty(name='Set range to strips')

    @classmethod
    def poll(cls, context):

        if context.area.type != 'NODE_EDITOR':
            return False

        if context.active_node and context.active_node.type == 'REROUTE':
            return True

        start = context.space_data.node_tree.nodes.get('Start', None)

        return start and start.type == 'REROUTE'

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.prop_search(self, 'target', bpy.data, 'texts')

        row = layout.row()
        row.prop(self, 'add_context_label')

        row = layout.row()
        row.prop(self, 'unfurl_to_vse')
        row.prop(self, 'set_range_to_strips')

        row = layout.row()
        row.prop(self, 'save_target')

        row = layout.row()
        row.prop(self, 'shell_command')
        row = layout.row()
        row.prop(self, 'shell_context')

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):

        if not self.target: return {'CANCELLED'}

        start = context.active_node
        if start.type != 'REROUTE':
            start = context.space_data.node_tree.nodes['Start']

        linked = find_linked(start)

        sum = ""

        last_context = ""

        for l in linked:
            parent = l.parent
            if not parent: continue

            if self.add_context_label:
                context_frame = parent.parent
                if context_frame:
                    current_context = context_frame.label
                    if current_context != last_context:
                        sum += f"\n{current_context}\n"
                        last_context = current_context

            label = parent.label

            if label: sum += "\n# {}\n\n".format(label)

            if parent.text:
                sum += '\n'.join([l.body for l in parent.text.lines])
                sum += '\n'

        text = bpy.data.texts.get(self.target.strip())
        text.clear()
        text.write(sum)

        if self.unfurl_to_vse:
            bpy.ops.unfurl.fountain_specific_to_strips(text=self.target)
            if self.set_range_to_strips:
                bpy.ops.sequencer.set_range_to_strips()

        if self.save_target:
            filepath = abspath(text.filepath or text.name_full)
            with open(filepath, 'w') as o:
                o.write(text.as_string())

        if self.shell_command:
            r = run(split(self.shell_command), cwd=abspath(self.shell_context))

        return {'FINISHED'}

def find_frame_and_tree(text):
    frame = None

    for g in bpy.data.node_groups:
        frames = [n for n in g.nodes if n.type == 'FRAME']

        try:
            frame = next(f for f in frames if  f.text == text)
            return frame, g
        except:
            continue

    return None, None

def find_text_offset(text, offset=1, stub_new=False):
    frame, tree = find_frame_and_tree(text)

    if not frame: return None

    start = tree.nodes.get('Start', None)

    if not start: return None

    linked = find_linked(start)

    if not stub_new:
        texts = [l.parent.text for l in linked if l.parent and l.parent.text]
    else:
        parents = [l.parent for l in linked if l.parent and l.parent]
        for p in parents:
            if not p.text:
                label = p.label or p.name
                new_text = bpy.data.texts.new(label)
                new_text.write('<+++>')
                p.text = new_text

        texts = [p.text for p in parents]

    current_index = texts.index(text)

    return texts[(current_index + offset) % len(texts)]

class NODE_OP_edit_next_text(Operator):
    bl_idname = "node.edit_next_text"
    bl_label = "Edit next text in linked texts"

    stub_new: BoolProperty('Stub new texts if missing', default=True)

    @classmethod
    def poll(cls, context):
        space = bpy.context.space_data
        return space.type == 'TEXT_EDITOR'

    def execute(self, context):
        text = context.space_data.text
        new_text = find_text_offset(text, 1, self.stub_new)

        if not new_text: return {'CANCELLED'}

        context.space_data.text = new_text
        return {'FINISHED'}

class NODE_OP_edit_prev_text(Operator):
    bl_idname = "node.edit_prev_text"
    bl_label = "Edit prev text in linked texts"

    stub_new: BoolProperty('Stub new texts if missing', default=True)

    @classmethod
    def poll(cls, context):
        space = bpy.context.space_data
        return space.type == 'TEXT_EDITOR'

    def execute(self, context):
        text = context.space_data.text
        new_text = find_text_offset(text, -1, self.stub_new)

        if not new_text: return {'CANCELLED'}

        context.space_data.text = new_text
        return {'FINISHED'}

def register():
    bpy.utils.register_class(NODE_OP_split_frame_from_lines)
    bpy.utils.register_class(NODE_OP_link_text)
    bpy.utils.register_class(NODE_OP_unlink_text)
    bpy.utils.register_class(NODE_OP_relink_text)
    bpy.utils.register_class(NODE_OP_collate_text)
    bpy.utils.register_class(NODE_OP_edit_next_text)
    bpy.utils.register_class(NODE_OP_edit_prev_text)
    bpy.utils.register_class(NODE_OP_post_to_texere)
    bpy.utils.register_class(NODE_OP_get_from_texere)
    bpy.utils.register_class(NODE_PT_texere_panel)

def unregister():
    bpy.utils.unregister_class(NODE_PT_texere_panel)
    bpy.utils.unregister_class(NODE_OP_post_to_texere)
    bpy.utils.unregister_class(NODE_OP_get_from_texere)
    bpy.utils.unregister_class(NODE_OP_edit_next_text)
    bpy.utils.unregister_class(NODE_OP_edit_prev_text)
    bpy.utils.unregister_class(NODE_OP_collate_text)
    bpy.utils.unregister_class(NODE_OP_relink_text)
    bpy.utils.unregister_class(NODE_OP_link_text)
    bpy.utils.unregister_class(NODE_OP_unlink_text)
    bpy.utils.unregister_class(NODE_OP_split_frame_from_lines)

if __name__ == "__main__":
    register()
