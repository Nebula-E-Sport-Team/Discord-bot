import discord
from discord.ext import commands
from datetime import datetime

class ServerChanges(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def log_change(self, change_type: str, details: str):
        """Enregistre un changement dans changes.txt"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{change_type}] {details}\n"
        
        with open("changes.txt", "a", encoding="utf-8") as f:
            f.write(log_entry)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        # Déterminer le type de canal
        if isinstance(channel, discord.ForumChannel):
            channel_type = "forum"
        elif isinstance(channel, discord.CategoryChannel):
            channel_type = "category"
        else:
            channel_type = "channel"
            
        details = (
            f"New {channel_type} created: {channel.name} "
            f"(ID: {channel.id})"
        )
        if not isinstance(channel, discord.CategoryChannel) and channel.category:
            details += f" in category {channel.category.name}"
        
        # Ajouter les tags si c'est un forum
        if isinstance(channel, discord.ForumChannel) and channel.available_tags:
            tags = ", ".join(tag.name for tag in channel.available_tags)
            details += f"\nAvailable tags: {tags}"
        
        self.log_change("CHANNEL_CREATE", details)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        channel_type = "category" if isinstance(channel, discord.CategoryChannel) else "channel"
        details = (
            f"{channel_type.capitalize()} deleted: {channel.name} "
            f"(ID: {channel.id})"
        )
        if not isinstance(channel, discord.CategoryChannel) and channel.category:
            details += f" from category {channel.category.name}"
        
        self.log_change("CHANNEL_DELETE", details)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        changes = []
        
        if before.name != after.name:
            changes.append(f"Name changed from '{before.name}' to '{after.name}'")
        
        if not isinstance(before, discord.CategoryChannel):
            if before.category != after.category:
                old_category = before.category.name if before.category else "No category"
                new_category = after.category.name if after.category else "No category"
                changes.append(f"Category changed from '{old_category}' to '{new_category}'")
        
        if isinstance(before, discord.TextChannel):
            if before.topic != after.topic:
                changes.append(
                    f"Topic changed from '{before.topic or 'None'}' "
                    f"to '{after.topic or 'None'}'"
                )
        
        # Gérer les changements spécifiques aux forums
        if isinstance(before, discord.ForumChannel):
            # Vérifier les changements de tags
            old_tags = {tag.name for tag in before.available_tags}
            new_tags = {tag.name for tag in after.available_tags}
            
            added_tags = new_tags - old_tags
            removed_tags = old_tags - new_tags
            
            if added_tags:
                changes.append(f"Added tags: {', '.join(added_tags)}")
            if removed_tags:
                changes.append(f"Removed tags: {', '.join(removed_tags)}")
        
        if changes:
            channel_type = "forum" if isinstance(after, discord.ForumChannel) else \
                         "category" if isinstance(after, discord.CategoryChannel) else \
                         "channel"
            details = (
                f"{channel_type.capitalize()} updated: {after.name} "
                f"(ID: {after.id})\nChanges:\n- " + "\n- ".join(changes)
            )
            self.log_change("CHANNEL_UPDATE", details)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        details = f"New role created: {role.name} (ID: {role.id})"
        self.log_change("ROLE_CREATE", details)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        details = f"Role deleted: {role.name} (ID: {role.id})"
        self.log_change("ROLE_DELETE", details)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        changes = []
        
        if before.name != after.name:
            changes.append(f"Name changed from '{before.name}' to '{after.name}'")
        
        if before.color != after.color:
            changes.append(f"Color changed from {before.color} to {after.color}")
        
        if before.permissions != after.permissions:
            # Trouver les permissions qui ont changé
            changed_perms = []
            for perm, value in after.permissions:
                if getattr(before.permissions, perm) != value:
                    changed_perms.append(f"{perm}: {value}")
            if changed_perms:
                changes.append("Permissions changed: " + ", ".join(changed_perms))
        
        if changes:
            details = (
                f"Role updated: {after.name} "
                f"(ID: {after.id})\nChanges:\n- " + "\n- ".join(changes)
            )
            self.log_change("ROLE_UPDATE", details)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Vérifier les changements de rôles
        added_roles = set(after.roles) - set(before.roles)
        removed_roles = set(before.roles) - set(after.roles)
        
        if added_roles:
            roles = ", ".join(role.name for role in added_roles)
            details = f"User {after.name}#{after.discriminator} (ID: {after.id}) received role(s): {roles}"
            self.log_change("MEMBER_ROLE_ADD", details)
        
        if removed_roles:
            roles = ", ".join(role.name for role in removed_roles)
            details = f"User {after.name}#{after.discriminator} (ID: {after.id}) lost role(s): {roles}"
            self.log_change("MEMBER_ROLE_REMOVE", details)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        if isinstance(thread.parent, discord.ForumChannel):
            details = (
                f"New forum post created: {thread.name} "
                f"(ID: {thread.id}) "
                f"in forum {thread.parent.name}"
            )
            
            # Ajouter les tags appliqués si présents
            if hasattr(thread, 'applied_tags') and thread.applied_tags:
                tags = ", ".join(tag.name for tag in thread.applied_tags)
                details += f"\nApplied tags: {tags}"
            
            self.log_change("FORUM_POST_CREATE", details)

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        if isinstance(after.parent, discord.ForumChannel):
            changes = []
            
            if before.name != after.name:
                changes.append(f"Title changed from '{before.name}' to '{after.name}'")
            
            # Vérifier les changements de tags
            if hasattr(before, 'applied_tags') and hasattr(after, 'applied_tags'):
                old_tags = {tag.name for tag in before.applied_tags}
                new_tags = {tag.name for tag in after.applied_tags}
                
                added_tags = new_tags - old_tags
                removed_tags = old_tags - new_tags
                
                if added_tags:
                    changes.append(f"Added tags: {', '.join(added_tags)}")
                if removed_tags:
                    changes.append(f"Removed tags: {', '.join(removed_tags)}")
            
            if changes:
                details = (
                    f"Forum post updated: {after.name} "
                    f"(ID: {after.id}) "
                    f"in forum {after.parent.name}\n"
                    f"Changes:\n- " + "\n- ".join(changes)
                )
                self.log_change("FORUM_POST_UPDATE", details)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        if isinstance(thread.parent, discord.ForumChannel):
            details = (
                f"Forum post deleted: {thread.name} "
                f"(ID: {thread.id}) "
                f"from forum {thread.parent.name}"
            )
            self.log_change("FORUM_POST_DELETE", details)

async def setup(bot):
    await bot.add_cog(ServerChanges(bot)) 