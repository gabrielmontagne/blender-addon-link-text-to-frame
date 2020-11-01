import bpy
from bpy.types import Operator
from bpy.path import abspath
from functools import reduce
from bpy.props import StringProperty, BoolProperty
from subprocess import run
from shlex import split

bl_info = {
    'name': 'Link Text to Node Frame',
    'author': 'gabriel montagné, gabriel@tibas.london',
    'version': (0, 0, 1),
    'blender': (2, 80, 0),
    'description': 'Quickly link a new text object to a frame node',
    'tracker_url': 'https://github.com/gabrielmontagne/blender-addon-link-text-to-frame/issues'
}

def find_linked(start):
    return reduce(linked_reroutes,[ start ], [])

def linked_reroutes(acc, start):
    result = acc + [ start ]
    to_nodes = [l.to_node for l in start.outputs[0].links if l.to_node]
    for n in to_nodes:
        result = reduce(linked_reroutes, to_nodes, result)
    return result

class NODE_OP_link_text(Operator):
    """Link text to frame"""
    bl_idname = "node.link_text_to_frame"
    bl_label = "Link Text to Frame"

    raise_in_editor: bpy.props.BoolProperty(name='Raise in editor', default=True)

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

class NODE_OP_collate_text(Operator):
    """Collate linked texts"""

    bl_idname = "node.collate_linked_frames"
    bl_label = "Collate all linked texts"

    save_target: BoolProperty(name='Save target')
    target: StringProperty(name='To file')
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

        for l in linked:
            parent = l.parent
            if not parent: continue

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
                print('Saved collate result to', filepath)

        if self.shell_command:
            print('run command', self.shell_command)
            r = run(split(self.shell_command), cwd=abspath(self.shell_context))

        return {'FINISHED'}

def find_frame_and_tree(text):
    frame = None

    for g in bpy.data.node_groups:
        print('ǵ', g)
        frames = [n for n in g.nodes if n.type == 'FRAME']
        print('frames', frames)

        try:
            frame = next(f for f in frames if  f.text == text)
            return frame, g
        except:
            continue

    return None, None

class NODE_OP_edit_next_text(Operator):
    bl_idname = "node.edit_next_text"
    bl_label = "Edit next text in linked texts"

    @classmethod
    def poll(cls, context):
        space = bpy.context.space_data
        return space.type == 'TEXT_EDITOR'

    def execute(self, context):
        text = context.space_data.text
        frame, tree = find_frame_and_tree(text)

        print('** FRAME', frame, tree)

        if not frame: return {'CANCELLED'}

        return {'FINISHED'}

class NODE_OP_edit_prev_text(Operator):
    bl_idname = "node.edit_prev_text"
    bl_label = "Edit prev text in linked texts"

    @classmethod
    def poll(cls, context):
        space = bpy.context.space_data
        return space.type == 'TEXT_EDITOR'

    def execute(self, context):
        print('exit prev text', context.space_data)
        return {'FINISHED'}

def register():
    bpy.utils.register_class(NODE_OP_link_text)
    bpy.utils.register_class(NODE_OP_collate_text)
    bpy.utils.register_class(NODE_OP_edit_next_text)
    bpy.utils.register_class(NODE_OP_edit_prev_text)

def unregister():
    bpy.utils.unregister_class(NODE_OP_edit_next_text)
    bpy.utils.unregister_class(NODE_OP_edit_prev_text)
    bpy.utils.unregister_class(NODE_OP_collate_text)
    bpy.utils.unregister_class(NODE_OP_link_text)

if __name__ == "__main__":
    register()
