from discord.ext import commands
import discord
import anthropic
import asyncio
from typing import Optional, Dict
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('eve_frontier_bot')

class EVEFrontierBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!EVE ",
            intents=intents,
            help_command=None  # We'll implement our own help command
        )
        
        # Initialize Anthropic client
        self.claude = anthropic.Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        
        # Initialize documentation manager (we'll implement this separately)
        self.doc_manager = None
        
        # Cache for recent queries
        self.query_cache: Dict[str, tuple] = {}
        
    async def setup_hook(self):
        """Setup bot and load extensions"""
        # Load command extensions
        await self.load_extension('cogs.smart_assemblies')
        await self.load_extension('cogs.documentation')
        await self.load_extension('cogs.help')
        
        # Initialize documentation manager
        # self.doc_manager = DocumentationManager()
        # await self.doc_manager.initialize()

    async def on_ready(self):
        """Called when bot is ready and connected"""
        logger.info(f'{self.user} has connected to Discord!')
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="EVE Frontier Development"
            )
        )

    async def on_command_error(self, ctx, error):
        """Global error handler"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Command not found. Use `!EVE help` for a list of commands.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
        else:
            logger.error(f'Error processing command: {error}')
            await ctx.send("An error occurred while processing your command.")

    async def get_claude_response(self, query: str, context: Optional[str] = None):
        """Get response from Claude with proper context"""
        try:
            system_prompt = f"""You are an EVE Frontier development assistant specializing in Smart Assembly creation and MUD framework integration.
            Your goal is to help developers create and modify Smart Assemblies.
            
            Current context:
            {context if context else 'No additional context provided'}
            """
            
            response = await asyncio.to_thread(
                self.claude.messages.create,
                model="claude-3-sonnet-20240229",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": query
                }],
                system=system_prompt
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f'Error getting Claude response: {e}')
            return "I encountered an error while processing your request."

    def split_response(self, response: str, chunk_size: int = 1990) -> list:
        """Split long responses into Discord-friendly chunks"""
        if len(response) <= chunk_size:
            return [response]
            
        chunks = []
        current_chunk = ""
        
        for line in response.split('\n'):
            if len(current_chunk) + len(line) + 1 > chunk_size:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                if current_chunk:
                    current_chunk += '\n'
                current_chunk += line
                
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

# Example command cog for Smart Assemblies
class SmartAssemblies(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name='smart')
    async def smart(self, ctx):
        """Smart Assembly related commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid smart assembly command. Use `!EVE help smart` for details.")

    @smart.command(name='create')
    async def create_assembly(self, ctx, assembly_type: str):
        """Create a new Smart Assembly"""
        # Get relevant documentation context
        context = await self.bot.doc_manager.get_assembly_docs(assembly_type)
        
        # Get guidance from Claude
        response = await self.bot.get_claude_response(
            f"How do I create a {assembly_type} Smart Assembly?",
            context
        )
        
        # Send response in chunks if needed
        for chunk in self.bot.split_response(response):
            await ctx.send(chunk)

async def setup(bot):
    await bot.add_cog(SmartAssemblies(bot))

# Main bot execution
def main():
    load_dotenv()
    
    bot = EVEFrontierBot()
    
    @bot.command(name='help')
    async def help_command(ctx):
        """Show help information"""
        help_text = """
        **EVE Frontier Development Assistant**
        
        **Basic Commands:**
        `!EVE help` - Show this help message
        `!EVE smart create <type>` - Get guidance on creating a Smart Assembly
        `!EVE docs search <query>` - Search documentation
        
        **Smart Assembly Types:**
        - Storage Unit (SSU)
        - Turret
        - Gate
        
        Use `!EVE help <command>` for more detailed information about a specific command.
        """
        await ctx.send(help_text)
    
    bot.run(os.getenv('DISCORD_TOKEN'))

if __name__ == "__main__":
    main()