from PIL import Image, ImageDraw, ImageFont
import io
import base64
import os
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class DiagramImageGenerator:
    def __init__(self):
        self.width = 1200
        self.height = 800
        self.bg_color = (248, 250, 252)
        self.azure_blue = (0, 120, 212)
        self.icons_base_path = "Azure_Public_Service_Icons_V23/Azure_Public_Service_Icons/Icons"
        
    def _create_azure_icon(self, service_name: str, category: str, size: int = 48) -> Image.Image:
        """Create Azure service icon with actual service symbols"""
        color = self._get_azure_category_color(category)
        color_rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        
        # Create icon with Azure service symbol
        icon = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(icon)
        
        # Draw Azure service icon background
        draw.rounded_rectangle([2, 2, size-2, size-2], radius=6, fill=color_rgb)
        
        # Get Azure service symbol
        symbol = self._get_azure_service_symbol(service_name)
        
        try:
            font = ImageFont.truetype("arial.ttf", size//2)
        except:
            font = ImageFont.load_default()
        
        # Center the symbol
        bbox = draw.textbbox((0, 0), symbol, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - 2
        
        draw.text((x, y), symbol, fill="white", font=font)
        
        return icon
    
    def _get_azure_service_symbol(self, service_name: str) -> str:
        """Get Azure service symbols"""
        symbols = {
            "virtual machine": "⚡",
            "app service": "🌐",
            "function": "ƒ",
            "sql database": "🗄",
            "cosmos db": "🌍",
            "storage account": "📦",
            "blob storage": "📦",
            "key vault": "🔐",
            "virtual network": "🔗",
            "vnet": "🔗",
            "application gateway": "🚪",
            "load balancer": "⚖",
            "front door": "🚪",
            "api management": "🔌",
            "redis cache": "⚡",
            "postgresql": "🐘",
            "mysql": "🐬",
            "monitor": "📊",
            "application insights": "📈",
            "log analytics": "📋"
        }
        
        service_lower = service_name.lower()
        for key, symbol in symbols.items():
            if key in service_lower:
                return symbol
        return "⚙"
        
    def generate_png_from_architecture(self, architecture: Dict[str, Any]) -> str:
        """Generate professional Azure architecture PNG with proper styling"""
        img = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        try:
            title_font = ImageFont.truetype("arial.ttf", 20)
            font = ImageFont.truetype("arial.ttf", 11)
            small_font = ImageFont.truetype("arial.ttf", 9)
        except:
            title_font = ImageFont.load_default()
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Azure header with gradient effect
        for i in range(80):
            color_intensity = int(255 * (1 - i/80 * 0.3))
            draw.rectangle([0, i, self.width, i+1], fill=(0, int(120 * color_intensity/255), int(212 * color_intensity/255)))
        
        # Microsoft Azure logo area
        draw.text((30, 25), "☁️ Microsoft Azure", fill="white", font=title_font)
        draw.text((30, 50), "Architecture Diagram", fill=(200, 220, 255), font=font)
        
        # Resource Group container with Azure styling
        rg_rect = [40, 100, self.width-40, self.height-60]
        draw.rectangle(rg_rect, outline=(147, 112, 219), width=3, fill=(250, 248, 255))
        draw.rectangle([45, 105, 200, 125], fill=(147, 112, 219))
        draw.text((50, 108), "📦 Resource Group", fill="white", font=font)
        
        services = architecture.get("services_with_icons", [])
        
        # Draw services with Azure-style icons
        for i, service in enumerate(services[:16]):  # Support up to 16 services
            col = i % 4
            row = i // 4
            x = 80 + col * 250
            y = 160 + row * 140
            
            category = service.get("icon_path", "").split("/")[0] if service.get("icon_path") else "general"
            color = self._get_azure_category_color(category)
            
            # Service container with Azure design
            service_rect = [x, y, x+180, y+100]
            draw.rectangle(service_rect, fill="white", outline=color, width=2)
            
            # Create professional Azure-style icon
            category = service.get("icon_path", "").split("/")[0] if service.get("icon_path") else "general"
            azure_icon = self._create_azure_icon(service["name"], category, 48)
            
            # Paste the Azure-style icon directly
            img.paste(azure_icon, (x+15, y+15), azure_icon)
            
            # Service name with proper Azure typography
            name = service["name"]
            if len(name) > 18:
                name = name[:15] + "..."
            draw.text((x+60, y+15), name, fill=(32, 31, 30), font=font)
            
            # Category badge
            category_text = category.replace('_', ' ').title()
            draw.rectangle([x+60, y+35, x+60+len(category_text)*7, y+50], fill=f"{color}30")
            draw.text((x+65, y+38), category_text, fill=color, font=small_font)
            
            # Service details
            draw.text((x+10, y+65), f"Region: {architecture.get('regions', ['East US'])[0]}", fill=(96, 94, 92), font=small_font)
            draw.text((x+10, y+80), f"Type: {category}", fill=(96, 94, 92), font=small_font)
        
        # Draw connections with Azure styling
        for i in range(min(len(services) - 1, 15)):
            source_col = i % 4
            source_row = i // 4
            target_col = (i + 1) % 4
            target_row = (i + 1) // 4
            
            x1 = 170 + source_col * 250
            y1 = 210 + source_row * 140
            x2 = 170 + target_col * 250
            y2 = 210 + target_row * 140
            
            # Azure-style connection lines
            draw.line([x1, y1, x2, y2], fill=self.azure_blue, width=3)
            
            # Connection arrow
            if x2 > x1:
                draw.polygon([(x2-10, y2-5), (x2, y2), (x2-10, y2+5)], fill=self.azure_blue)
            elif x2 < x1:
                draw.polygon([(x2+10, y2-5), (x2, y2), (x2+10, y2+5)], fill=self.azure_blue)
        
        # Footer with Azure branding
        draw.rectangle([0, self.height-40, self.width, self.height], fill=(243, 242, 241))
        draw.text((30, self.height-30), f"Services: {len(services)} • Cost: {architecture.get('estimated_cost', 'N/A')}", fill=(96, 94, 92), font=font)
        draw.text((self.width-200, self.height-30), "Generated by Azure AI", fill=(96, 94, 92), font=font)
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', quality=95)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def _get_azure_category_color(self, category: str) -> str:
        """Get Azure official colors for categories"""
        colors = {
            "compute": "#FF6900",
            "storage": "#00BCF2", 
            "databases": "#BA68C8",
            "networking": "#4CAF50",
            "security": "#F44336",
            "analytics": "#FF9800",
            "ai + machine learning": "#9C27B0",
            "integration": "#607D8B",
            "monitor": "#795548",
            "web": "#2196F3",
            "iot": "#009688"
        }
        return colors.get(category, "#0078D4")
    
    def generate_from_drawio(self, drawio_xml: str, output_path: str) -> bool:
        """Generate PNG image from Draw.io XML (fallback implementation)"""
        try:
            logger.info(f"Attempting to generate PNG from Draw.io XML to {output_path}")
            
            # Parse basic structure from XML to create a simple diagram
            import re
            from xml.etree import ElementTree as ET
            
            # Extract service names from the XML
            services = []
            try:
                root = ET.fromstring(drawio_xml)
                # Look for text elements in the XML that might be service names
                for elem in root.iter():
                    text = elem.get('value', '') or elem.text or ''
                    if text and len(text.strip()) > 2 and not any(x in text.lower() for x in ['mxgraph', 'geometry', 'style']):
                        # Clean up the text
                        cleaned_text = re.sub(r'[<>]', '', text).strip()
                        if cleaned_text and len(cleaned_text) > 2:
                            services.append({"name": cleaned_text, "icon_path": "general/service"})
            except Exception as xml_error:
                logger.warning(f"Could not parse XML for services: {xml_error}")
                # Use fallback services
                services = [
                    {"name": "Azure Service 1", "icon_path": "compute/virtual_machine"},
                    {"name": "Azure Service 2", "icon_path": "storage/storage_account"},
                    {"name": "Azure Service 3", "icon_path": "networking/virtual_network"}
                ]
            
            # Limit services to prevent overcrowding
            services = services[:12]
            
            # Create architecture object for PNG generation
            architecture = {
                "services_with_icons": services,
                "regions": ["East US"],
                "estimated_cost": "$200-500/month"
            }
            
            # Generate PNG using the existing method
            png_base64 = self.generate_png_from_architecture(architecture)
            
            # Save to file
            if png_base64.startswith('data:image/png;base64,'):
                image_data = png_base64.split(',')[1]
            else:
                image_data = png_base64
                
            with open(output_path, 'wb') as f:
                f.write(base64.b64decode(image_data))
            
            logger.info(f"✅ PNG image successfully generated: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating PNG from Draw.io XML: {e}")
            return False
    
    def _get_azure_service_icon(self, service_name: str) -> str:
        """Get Unicode icons for Azure services"""
        icons = {
            "virtual machine": "🖥️",
            "app service": "🌐",
            "function": "⚡",
            "sql database": "🗄️",
            "cosmos db": "🌌",
            "storage account": "💾",
            "blob storage": "📦",
            "key vault": "🔐",
            "virtual network": "🏢",
            "vnet": "🏢",
            "load balancer": "⚖️",
            "application gateway": "🚪",
            "gateway": "🚪",
            "front door": "🚪",
            "cdn": "🌐",
            "kubernetes": "☸️",
            "container": "📦",
            "redis": "🔴",
            "mysql": "🐬",
            "postgresql": "🐘",
            "monitor": "📊",
            "analytics": "📈",
            "databricks": "🧱",
            "cognitive": "🧠",
            "bot": "🤖",
            "logic apps": "🔗",
            "event": "📡"
        }
        
        service_lower = service_name.lower()
        for key, icon in icons.items():
            if key in service_lower:
                return icon
        return "⚙️"