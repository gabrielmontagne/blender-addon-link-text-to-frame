import bpy
from functools import reduce

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

class NODE_OP_link_text(bpy.types.Operator):
    """Link text to frame"""
    bl_idname = "node.link_text_to_frame"
    bl_label = "Link Text to Frame"

    raise_in_editor: bpy.props.BoolProperty(name='Raise in editor', default=True)

    @classmethod
    def poll(cls, context):
        return context.area.type == 'NODE_EDITOR' and context.active_node and context.active_node.type == 'FRAME' and context.active_node.label

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        active_node = bpy.context.active_node
        label = active_node.label
        text = active_node.text

        if not text:
            text = bpy.data.texts.new(label)
            text.write('<+++>')
            active_node.text = text

        if self.raise_in_editor:
            for area in bpy.context.screen.areas:
                if area.type == 'TEXT_EDITOR':
                    area.spaces[0].text = text

        return {'FINISHED'}

class NODE_OP_collate_text(bpy.types.Operator):
    """Collate linked texts"""
    bl_idname = "node.cllate_linked_frames"
    bl_label = "Collate all linked texts"

    @classmethod
    def poll(cls, context):
        return context.area.type == 'NODE_EDITOR' and context.active_node and context.active_node.type == 'REROUTE' 

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):

        print('→')
        linked = find_linked(context.active_node)

        sum = ""

        for l in linked:
            parent = l.parent
            if not parent: continue

            label = parent.label or parent.name

            sum += "\n# {}\n\n".format(label)

            if parent.text:
                sum += '\n'.join([l.body for l in parent.text.lines])
                sum += '\n'


        print(sum)
        return {'FINISHED'}

def register():
    bpy.utils.register_class(NODE_OP_link_text)
    bpy.utils.register_class(NODE_OP_collate_text)

def unregister():
    bpy.utils.unregister_class(NODE_OP_collate_text)
    bpy.utils.unregister_class(NODE_OP_link_text)

if __name__ == "__main__":
    register()