import bpy
from bpy.props import BoolProperty

class NODE_OP_link_text(bpy.types.Operator):
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
        return {'FINISHED'}

def register():
    print('register')
    bpy.utils.register_class(NODE_OP_link_text)

def unregister():
    bpy.utils.unregister_class(NODE_OP_link_text)

if __name__ == "__main__":
    register()
