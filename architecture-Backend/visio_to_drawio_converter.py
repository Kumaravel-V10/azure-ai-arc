"""
Visio (.vsdx) to Draw.io (.drawio) Converter
Batch converts Microsoft Visio files to Draw.io XML format
"""

import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import uuid
import re
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import drawio_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class VisioShape:
    """Represents a shape from Visio"""
    id: str
    name: str
    text: str
    x: float
    y: float
    width: float
    height: float
    shape_type: str
    master_name: str = ""
    fill_color: str = "#FFFFFF"
    line_color: str = "#000000"
    connects_from: List[str] = None
    connects_to: List[str] = None
    
    def __post_init__(self):
        if self.connects_from is None:
            self.connects_from = []
        if self.connects_to is None:
            self.connects_to = []


@dataclass
class VisioConnection:
    """Represents a connection/connector from Visio"""
    id: str
    from_shape_id: str
    to_shape_id: str
    label: str = ""


class VisioParser:
    """Parse Visio .vsdx files (which are ZIP archives with XML content)"""
    
    NAMESPACES = {
        'v': 'http://schemas.microsoft.com/office/visio/2012/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    }
    
    def __init__(self, vsdx_path: str):
        self.vsdx_path = vsdx_path
        self.shapes: List[VisioShape] = []
        self.connections: List[VisioConnection] = []
        self.pages: List[Dict] = []
        
    def parse(self) -> Dict[str, Any]:
        """Parse the VSDX file and extract shapes and connections"""
        try:
            with zipfile.ZipFile(self.vsdx_path, 'r') as vsdx:
                # List all files in the archive for debugging
                file_list = vsdx.namelist()
                logger.debug(f"Files in VSDX: {file_list}")
                
                # Parse pages
                self._parse_pages(vsdx)
                
                # Parse masters (shape templates)
                masters = self._parse_masters(vsdx)
                
                # Parse document relationships
                self._parse_relationships(vsdx)
                
            return {
                'shapes': self.shapes,
                'connections': self.connections,
                'pages': self.pages,
                'file_name': os.path.basename(self.vsdx_path)
            }
            
        except zipfile.BadZipFile:
            logger.error(f"Invalid VSDX file: {self.vsdx_path}")
            raise ValueError(f"Invalid VSDX file: {self.vsdx_path}")
        except Exception as e:
            logger.error(f"Error parsing VSDX: {str(e)}")
            raise
    
    def _parse_pages(self, vsdx: zipfile.ZipFile):
        """Parse all pages in the Visio document"""
        # Try to find pages.xml or individual page files
        page_files = [f for f in vsdx.namelist() if 'pages/page' in f.lower() and f.endswith('.xml')]
        
        if not page_files:
            # Try alternative structure
            page_files = [f for f in vsdx.namelist() if 'page1.xml' in f.lower()]
        
        for page_file in page_files:
            try:
                with vsdx.open(page_file) as pf:
                    content = pf.read()
                    self._parse_page_xml(content, page_file)
            except Exception as e:
                logger.warning(f"Could not parse page {page_file}: {e}")
    
    def _parse_page_xml(self, content: bytes, page_name: str):
        """Parse the XML content of a page"""
        try:
            root = ET.fromstring(content)
            
            # Find all shapes
            shapes_elem = root.findall('.//v:Shape', self.NAMESPACES)
            if not shapes_elem:
                # Try without namespace
                shapes_elem = root.findall('.//Shape')
            
            for shape_elem in shapes_elem:
                shape = self._parse_shape_element(shape_elem)
                if shape:
                    self.shapes.append(shape)
            
            # Find connections
            connects = root.findall('.//v:Connect', self.NAMESPACES)
            if not connects:
                connects = root.findall('.//Connect')
                
            for connect in connects:
                self._parse_connect_element(connect)
                
            self.pages.append({
                'name': page_name,
                'shape_count': len(shapes_elem)
            })
                
        except ET.ParseError as e:
            logger.warning(f"XML parse error in page {page_name}: {e}")
    
    def _parse_shape_element(self, shape_elem: ET.Element) -> Optional[VisioShape]:
        """Parse a single shape element"""
        try:
            shape_id = shape_elem.get('ID', str(uuid.uuid4())[:8])
            shape_name = shape_elem.get('Name', '') or shape_elem.get('NameU', '')
            shape_type = shape_elem.get('Type', 'Shape')
            master_name = shape_elem.get('Master', '')
            
            # Get geometry (position and size)
            x, y = 0.0, 0.0
            width, height = 100.0, 60.0  # Default size
            
            # Try to get XForm (transform) data
            xform = shape_elem.find('.//v:XForm', self.NAMESPACES)
            if xform is None:
                xform = shape_elem.find('.//XForm')
            
            if xform is not None:
                pin_x = xform.find('.//v:PinX', self.NAMESPACES)
                if pin_x is None:
                    pin_x = xform.find('.//PinX')
                if pin_x is not None and pin_x.text:
                    x = self._parse_unit_value(pin_x.text)
                
                pin_y = xform.find('.//v:PinY', self.NAMESPACES)
                if pin_y is None:
                    pin_y = xform.find('.//PinY')
                if pin_y is not None and pin_y.text:
                    y = self._parse_unit_value(pin_y.text)
                
                width_elem = xform.find('.//v:Width', self.NAMESPACES)
                if width_elem is None:
                    width_elem = xform.find('.//Width')
                if width_elem is not None and width_elem.text:
                    width = self._parse_unit_value(width_elem.text) * 96  # Convert to pixels
                
                height_elem = xform.find('.//v:Height', self.NAMESPACES)
                if height_elem is None:
                    height_elem = xform.find('.//Height')
                if height_elem is not None and height_elem.text:
                    height = self._parse_unit_value(height_elem.text) * 96  # Convert to pixels
            
            # Get text content
            text = ""
            text_elem = shape_elem.find('.//v:Text', self.NAMESPACES)
            if text_elem is None:
                text_elem = shape_elem.find('.//Text')
            if text_elem is not None:
                text = ''.join(text_elem.itertext()).strip()
            
            # Get fill color
            fill_color = "#FFFFFF"
            fill = shape_elem.find('.//v:FillForegnd', self.NAMESPACES)
            if fill is None:
                fill = shape_elem.find('.//FillForegnd')
            if fill is not None and fill.text:
                fill_color = self._parse_color(fill.text)
            
            # Get line color
            line_color = "#000000"
            line = shape_elem.find('.//v:LineColor', self.NAMESPACES)
            if line is None:
                line = shape_elem.find('.//LineColor')
            if line is not None and line.text:
                line_color = self._parse_color(line.text)
            
            # Convert coordinates (Visio uses inches, Draw.io uses pixels)
            x = x * 96  # 96 DPI
            y = y * 96
            
            return VisioShape(
                id=shape_id,
                name=shape_name,
                text=text or shape_name,
                x=x,
                y=y,
                width=max(width, 80),
                height=max(height, 40),
                shape_type=shape_type,
                master_name=master_name,
                fill_color=fill_color,
                line_color=line_color
            )
            
        except Exception as e:
            logger.warning(f"Could not parse shape: {e}")
            return None
    
    def _parse_connect_element(self, connect_elem: ET.Element):
        """Parse a connection element"""
        try:
            from_sheet = connect_elem.get('FromSheet', '')
            to_sheet = connect_elem.get('ToSheet', '')
            
            if from_sheet and to_sheet:
                connection = VisioConnection(
                    id=str(uuid.uuid4())[:8],
                    from_shape_id=from_sheet,
                    to_shape_id=to_sheet
                )
                self.connections.append(connection)
                
        except Exception as e:
            logger.warning(f"Could not parse connection: {e}")
    
    def _parse_masters(self, vsdx: zipfile.ZipFile) -> Dict[str, Any]:
        """Parse master shapes (templates)"""
        masters = {}
        master_files = [f for f in vsdx.namelist() if 'masters/' in f.lower() and f.endswith('.xml')]
        
        for master_file in master_files:
            try:
                with vsdx.open(master_file) as mf:
                    # Parse master definitions
                    pass  # Implement if needed for more detailed shape info
            except Exception:
                pass
                
        return masters
    
    def _parse_relationships(self, vsdx: zipfile.ZipFile):
        """Parse document relationships"""
        rels_files = [f for f in vsdx.namelist() if '.rels' in f.lower()]
        # Can be extended to understand document structure better
    
    def _parse_unit_value(self, value: str) -> float:
        """Parse a Visio unit value (can include units like 'IN', 'MM', etc.)"""
        try:
            # Remove unit suffixes
            clean_value = re.sub(r'[A-Za-z]+$', '', value.strip())
            return float(clean_value)
        except (ValueError, AttributeError):
            return 0.0
    
    def _parse_color(self, color_value: str) -> str:
        """Parse Visio color value to hex"""
        try:
            # Handle indexed colors or RGB values
            if color_value.startswith('#'):
                return color_value
            
            # Try to parse as integer (Visio sometimes uses decimal RGB)
            if color_value.isdigit():
                int_val = int(color_value)
                r = int_val & 0xFF
                g = (int_val >> 8) & 0xFF
                b = (int_val >> 16) & 0xFF
                return f"#{r:02x}{g:02x}{b:02x}"
            
            return "#FFFFFF"
        except:
            return "#FFFFFF"


class DrawioGenerator:
    """Generate Draw.io XML from parsed Visio data"""
    
    # Azure service color mappings
    AZURE_COLORS = {
        'default': '#0078D4',  # Azure blue
        'compute': '#0078D4',
        'storage': '#00BCF2',
        'database': '#5C2D91',
        'networking': '#FF8C00',
        'security': '#E81123',
        'ai': '#107C10',
        'analytics': '#00188F'
    }
    
    def __init__(self):
        self.shape_id_counter = 1
        self.shape_id_map: Dict[str, str] = {}  # Map Visio IDs to Draw.io IDs
    
    def generate(self, visio_data: Dict[str, Any], diagram_name: str = "Converted Architecture") -> str:
        """Generate Draw.io XML from parsed Visio data"""
        
        # Create root mxfile element
        mxfile = ET.Element('mxfile')
        mxfile.set('host', 'app.diagrams.net')
        mxfile.set('modified', '2024-01-01T00:00:00.000Z')
        mxfile.set('agent', 'Visio Converter')
        mxfile.set('version', '21.0.0')
        mxfile.set('type', 'device')
        
        # Create diagram
        diagram = ET.SubElement(mxfile, 'diagram')
        diagram.set('name', diagram_name)
        diagram.set('id', str(uuid.uuid4())[:12])
        
        # Create mxGraphModel
        model = ET.SubElement(diagram, 'mxGraphModel')
        model.set('dx', '1434')
        model.set('dy', '780')
        model.set('grid', '1')
        model.set('gridSize', '10')
        model.set('guides', '1')
        model.set('tooltips', '1')
        model.set('connect', '1')
        model.set('arrows', '1')
        model.set('fold', '1')
        model.set('page', '1')
        model.set('pageScale', '1')
        model.set('pageWidth', str(drawio_config.FALLBACK_PAGE_WIDTH))
        model.set('pageHeight', str(drawio_config.FALLBACK_PAGE_HEIGHT))
        model.set('math', '0')
        model.set('shadow', '0')
        
        # Create root cell container
        root = ET.SubElement(model, 'root')
        
        # Add required parent cells
        cell0 = ET.SubElement(root, 'mxCell')
        cell0.set('id', '0')
        
        cell1 = ET.SubElement(root, 'mxCell')
        cell1.set('id', '1')
        cell1.set('parent', '0')
        
        # Convert shapes
        shapes = visio_data.get('shapes', [])
        self._normalize_positions(shapes)
        
        for shape in shapes:
            self._add_shape(root, shape)
        
        # Convert connections
        connections = visio_data.get('connections', [])
        for conn in connections:
            self._add_connection(root, conn)
        
        # Generate pretty XML
        return self._prettify_xml(mxfile)
    
    def _normalize_positions(self, shapes: List[VisioShape]):
        """Normalize positions to fit within diagram bounds"""
        if not shapes:
            return
            
        # Find min/max coordinates
        min_x = min(s.x for s in shapes) if shapes else 0
        min_y = min(s.y for s in shapes) if shapes else 0
        
        # Offset all shapes so minimum is at 50,50
        offset_x = 50 - min_x
        offset_y = 50 - min_y
        
        for shape in shapes:
            shape.x += offset_x
            shape.y += offset_y
            
            # Ensure positive coordinates
            shape.x = max(20, shape.x)
            shape.y = max(20, shape.y)
    
    def _add_shape(self, root: ET.Element, shape: VisioShape) -> str:
        """Add a shape to the Draw.io diagram"""
        cell_id = str(self.shape_id_counter + 1)
        self.shape_id_counter += 1
        
        # Map Visio ID to Draw.io ID
        self.shape_id_map[shape.id] = cell_id
        
        cell = ET.SubElement(root, 'mxCell')
        cell.set('id', cell_id)
        cell.set('value', self._escape_xml(shape.text))
        cell.set('parent', '1')
        cell.set('vertex', '1')
        
        # Determine style based on shape characteristics
        style = self._generate_style(shape)
        cell.set('style', style)
        
        # Add geometry
        geometry = ET.SubElement(cell, 'mxGeometry')
        geometry.set('x', str(int(shape.x)))
        geometry.set('y', str(int(shape.y)))
        geometry.set('width', str(int(shape.width)))
        geometry.set('height', str(int(shape.height)))
        geometry.set('as', 'geometry')
        
        return cell_id
    
    def _add_connection(self, root: ET.Element, conn: VisioConnection):
        """Add a connection/edge to the Draw.io diagram"""
        # Get mapped IDs
        source_id = self.shape_id_map.get(conn.from_shape_id)
        target_id = self.shape_id_map.get(conn.to_shape_id)
        
        if not source_id or not target_id:
            return
        
        cell_id = str(self.shape_id_counter + 1)
        self.shape_id_counter += 1
        
        cell = ET.SubElement(root, 'mxCell')
        cell.set('id', cell_id)
        cell.set('value', conn.label)
        cell.set('parent', '1')
        cell.set('edge', '1')
        cell.set('source', source_id)
        cell.set('target', target_id)
        
        # Edge style
        style = 'edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeWidth=2;strokeColor=#666666;'
        cell.set('style', style)
        
        # Add geometry for edge
        geometry = ET.SubElement(cell, 'mxGeometry')
        geometry.set('relative', '1')
        geometry.set('as', 'geometry')
    
    def _generate_style(self, shape: VisioShape) -> str:
        """Generate Draw.io style string for a shape"""
        # Check if it's an Azure service
        is_azure = self._detect_azure_service(shape)
        
        fill_color = shape.fill_color if shape.fill_color != "#FFFFFF" else self.AZURE_COLORS['default']
        
        # Base style options
        style_parts = [
            'rounded=1',
            'whiteSpace=wrap',
            'html=1',
            f'fillColor={fill_color}',
            f'strokeColor={shape.line_color}',
            'strokeWidth=2',
            'fontColor=#FFFFFF' if self._is_dark_color(fill_color) else 'fontColor=#333333',
            'fontSize=12',
            'fontStyle=1',  # Bold
            'shadow=1'
        ]
        
        # Add shape-specific styling
        if 'database' in shape.name.lower() or 'sql' in shape.name.lower() or 'cosmos' in shape.name.lower():
            style_parts.append('shape=cylinder3')
            style_parts.append('size=15')
        elif 'function' in shape.name.lower() or 'lambda' in shape.name.lower():
            style_parts.append('shape=hexagon')
        elif 'gateway' in shape.name.lower() or 'load balancer' in shape.name.lower():
            style_parts.append('shape=trapezoid')
        elif 'storage' in shape.name.lower() or 'blob' in shape.name.lower():
            style_parts.append('shape=parallelogram')
        
        return ';'.join(style_parts) + ';'
    
    def _detect_azure_service(self, shape: VisioShape) -> bool:
        """Detect if shape represents an Azure service"""
        azure_keywords = [
            'azure', 'microsoft', 'app service', 'function', 'cosmos', 
            'sql', 'storage', 'blob', 'key vault', 'api management',
            'front door', 'application gateway', 'virtual network', 'aks'
        ]
        shape_text = (shape.name + ' ' + shape.text).lower()
        return any(kw in shape_text for kw in azure_keywords)
    
    def _is_dark_color(self, hex_color: str) -> bool:
        """Check if a color is dark (for font color contrast)"""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return luminance < 0.5
        except:
            return False
    
    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters"""
        if not text:
            return ""
        return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))
    
    def _prettify_xml(self, elem: ET.Element) -> str:
        """Return a pretty-printed XML string"""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")


class VisioToDrawioConverter:
    """Main converter class for batch processing"""
    
    def __init__(self, input_dir: str, output_dir: str = None):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir) if output_dir else self.input_dir / 'drawio_output'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[Dict] = []
    
    def convert_single(self, vsdx_path: str | Path) -> Tuple[bool, str, str]:
        """Convert a single VSDX file to Draw.io format"""
        vsdx_path = Path(vsdx_path)
        output_path = self.output_dir / (vsdx_path.stem + '.drawio')
        
        try:
            logger.info(f"Converting: {vsdx_path.name}")
            
            # Parse Visio file
            parser = VisioParser(str(vsdx_path))
            visio_data = parser.parse()
            
            # Generate Draw.io XML
            generator = DrawioGenerator()
            drawio_xml = generator.generate(visio_data, vsdx_path.stem)
            
            # Write output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(drawio_xml)
            
            shape_count = len(visio_data.get('shapes', []))
            conn_count = len(visio_data.get('connections', []))
            
            logger.info(f"  ✓ Converted: {output_path.name} ({shape_count} shapes, {conn_count} connections)")
            return True, str(output_path), f"Success: {shape_count} shapes, {conn_count} connections"
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"  ✗ Failed: {vsdx_path.name} - {error_msg}")
            return False, str(output_path), error_msg
    
    def convert_all(self, max_workers: int = 4) -> Dict[str, Any]:
        """Convert all VSDX files in the input directory"""
        vsdx_files = list(self.input_dir.glob('*.vsdx'))
        
        if not vsdx_files:
            logger.warning(f"No .vsdx files found in {self.input_dir}")
            return {'success': 0, 'failed': 0, 'files': []}
        
        logger.info(f"Found {len(vsdx_files)} Visio files to convert")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info("-" * 50)
        
        success_count = 0
        failed_count = 0
        
        # Process files (can use ThreadPoolExecutor for parallel processing)
        for vsdx_file in vsdx_files:
            success, output_path, message = self.convert_single(vsdx_file)
            
            self.results.append({
                'input': str(vsdx_file),
                'output': output_path,
                'success': success,
                'message': message
            })
            
            if success:
                success_count += 1
            else:
                failed_count += 1
        
        logger.info("-" * 50)
        logger.info(f"Conversion complete: {success_count} succeeded, {failed_count} failed")
        
        return {
            'success': success_count,
            'failed': failed_count,
            'total': len(vsdx_files),
            'output_dir': str(self.output_dir),
            'files': self.results
        }


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Convert Visio (.vsdx) files to Draw.io (.drawio) format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python visio_to_drawio_converter.py ../visiofiles
  python visio_to_drawio_converter.py ../visiofiles -o ./converted
  python visio_to_drawio_converter.py -f single_file.vsdx
        """
    )
    
    parser.add_argument('input_path', nargs='?', default='../visiofiles',
                        help='Input directory containing .vsdx files or single file path')
    parser.add_argument('-o', '--output', default=None,
                        help='Output directory for .drawio files')
    parser.add_argument('-f', '--file', default=None,
                        help='Convert a single file instead of directory')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.file:
        # Single file conversion
        input_path = Path(args.file)
        output_dir = Path(args.output) if args.output else input_path.parent
        
        converter = VisioToDrawioConverter(str(input_path.parent), str(output_dir))
        success, output_path, message = converter.convert_single(input_path)
        
        if success:
            print(f"\n✓ Successfully converted to: {output_path}")
        else:
            print(f"\n✗ Conversion failed: {message}")
            sys.exit(1)
    else:
        # Batch conversion
        input_dir = Path(args.input_path)
        
        if not input_dir.exists():
            print(f"Error: Input directory not found: {input_dir}")
            sys.exit(1)
        
        output_dir = args.output if args.output else str(input_dir / 'drawio_output')
        
        converter = VisioToDrawioConverter(str(input_dir), output_dir)
        results = converter.convert_all()
        
        print(f"\n{'='*50}")
        print(f"CONVERSION SUMMARY")
        print(f"{'='*50}")
        print(f"Total files:     {results['total']}")
        print(f"Successful:      {results['success']}")
        print(f"Failed:          {results['failed']}")
        print(f"Output location: {results['output_dir']}")
        
        if results['failed'] > 0:
            print(f"\nFailed files:")
            for f in results['files']:
                if not f['success']:
                    print(f"  - {Path(f['input']).name}: {f['message']}")


if __name__ == '__main__':
    main()
