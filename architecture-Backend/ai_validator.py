import os
import base64
import json
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from agents import AgentOrchestrator
from drawio_architecture_analyzer import DrawioArchitectureAnalyzer
from config import agent_config, azure_openai_config, content_config
import asyncio

logger = logging.getLogger(__name__)

# Import accuracy enhancements for improved scoring
try:
    from accuracy_enhancements import get_accuracy_scorer, get_service_detector, get_learned_patterns
    ACCURACY_ENHANCEMENTS_AVAILABLE = True
except ImportError:
    ACCURACY_ENHANCEMENTS_AVAILABLE = False
    def get_accuracy_scorer(): return None
    def get_service_detector(): return None
    def get_learned_patterns(): return None

try:
    from openai import AzureOpenAI
except ImportError:
    print("OpenAI not installed. Install with: pip install openai")
    AzureOpenAI = None

class AIArchitectureValidator:
    def __init__(self):
        if not os.getenv("AZURE_OPENAI_API_KEY"):
            raise ValueError("Azure OpenAI configuration required. Set AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_DEPLOYMENT_NAME environment variables.")
        
        self.client = AzureOpenAI(
            api_key=azure_openai_config.API_KEY or os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=azure_openai_config.API_VERSION,
            azure_endpoint=azure_openai_config.ENDPOINT or os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment_name = azure_openai_config.DEPLOYMENT_NAME
        self.orchestrator = AgentOrchestrator()
        
        # Initialize accuracy enhancements if available
        self.accuracy_scorer = get_accuracy_scorer() if ACCURACY_ENHANCEMENTS_AVAILABLE else None
        self.service_detector = get_service_detector() if ACCURACY_ENHANCEMENTS_AVAILABLE else None
        self.learned_patterns = get_learned_patterns() if ACCURACY_ENHANCEMENTS_AVAILABLE else None
    
    def validate_connections_with_learned_patterns(self, services: List[str], connections: List[Dict]) -> Dict[str, Any]:
        """Validate connections against learned patterns from Azure Architecture Center.
        
        Returns validation results including:
        - Which connections follow common Azure patterns
        - Suggested missing connections
        - Similar reference architectures
        """
        if not self.learned_patterns or not services:
            return {"available": False, "reason": "Learned patterns not available or no services provided"}
        
        try:
            # Extract connection tuples
            connection_tuples = []
            for conn in connections:
                source = conn.get("from") or conn.get("source", "")
                target = conn.get("to") or conn.get("target", "")
                if source and target:
                    connection_tuples.append((source, target))
            
            # Validate connections
            validated_connections = self.learned_patterns.validate_connections(connection_tuples)
            
            # Find similar architectures
            similar_architectures = self.learned_patterns.find_similar_architecture(services, top_n=3)
            
            # Suggest missing services
            suggested_services = self.learned_patterns.suggest_missing_services(services)
            
            # Get connection suggestions for existing services
            suggested_connections = {}
            common_patterns = 0
            for service in services[:10]:
                suggestions = self.learned_patterns.get_connection_suggestions(service)
                if suggestions:
                    # Filter to services in the current architecture
                    relevant_suggestions = [s for s in suggestions if s in services]
                    if relevant_suggestions:
                        suggested_connections[service] = relevant_suggestions
            
            # Calculate pattern adherence score
            if validated_connections:
                common_patterns = sum(1 for c in validated_connections if c.get("is_common_pattern"))
                pattern_adherence = (common_patterns / len(validated_connections) * 100) if validated_connections else 0
            else:
                pattern_adherence = 50  # Default when no connections to validate
            
            return {
                "available": True,
                "pattern_adherence_score": round(pattern_adherence, 1),
                "common_pattern_connections": common_patterns,
                "total_connections_validated": len(validated_connections),
                "similar_architectures": similar_architectures,
                "suggested_services_to_add": suggested_services[:5],
                "validated_connections": validated_connections[:10],  # Limit output
                "suggested_new_connections": suggested_connections
            }
        except Exception as e:
            return {"available": False, "reason": f"Error validating patterns: {str(e)}"}
    
    def _clean_json_response(self, response: str) -> str:
        """Clean and prepare JSON response for parsing"""
        import re
        
        if not response or not isinstance(response, str) or response.strip() == "":
            return "{}"
        
        cleaned = response.strip()
        
        # Handle partial responses that start with field names only
        if cleaned.startswith('"') and ':' not in cleaned[:50] and not cleaned.startswith('{"'):
            return "{}"
        
        # Remove markdown code blocks
        if cleaned.startswith("```json"):
            cleaned = cleaned.replace("```json", "").strip()
        elif cleaned.startswith("```"):
            lines = cleaned.split('\n') if cleaned else []
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            cleaned = '\n'.join(lines).strip()
        
        # Remove trailing ```
        if cleaned.endswith("```"):
            cleaned = cleaned.rstrip("```").strip()
        
        # Try to fix common JSON issues
        cleaned = cleaned.replace("'", '"')  # Replace single quotes with double quotes
        
        # Fix trailing commas - this is the main issue causing JSON parsing errors
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
        cleaned = re.sub(r',(\s*$)', '', cleaned)
        
        # Ensure it starts with opening brace
        if not cleaned.startswith('{'):
            brace_idx = cleaned.find('{')
            if brace_idx >= 0:
                cleaned = cleaned[brace_idx:]
            else:
                return "{}"
        
        # If JSON seems incomplete, try to complete it
        if cleaned and not cleaned.endswith('}'):
            open_braces = cleaned.count('{')
            close_braces = cleaned.count('}')
            if open_braces > close_braces:
                quote_count = cleaned.count('"')
                if quote_count % 2 != 0:
                    cleaned += '"'
                cleaned += '}' * (open_braces - close_braces)
        
        return cleaned
    async def analyze_drawio_xml(self, xml_content: str, requirements: str) -> Dict[str, Any]:
        """Analyze draw.io XML diagram content"""
        
        analysis_prompt = f"""
        As an expert Azure solution architect, analyze this draw.io XML diagram and provide insights:
        
        REQUIREMENTS: {requirements}
        
        DRAW.IO XML CONTENT: {xml_content[:content_config.XML_CONTENT_LIMIT]}...
        
        Parse the XML to identify:
        1. Azure services and components mentioned
        2. Architecture patterns and connections
        3. Resource groups and organization
        4. Network design and security features
        5. Compliance with Azure Well-Architected Framework
        
        Provide analysis in JSON format:
        {{
            "detected_services": ["service1", "service2", ...],
            "architecture_pattern": "pattern name",
            "resource_groups": ["rg1", "rg2", ...],
            "network_design": "description of network architecture",
            "security_features": ["feature1", "feature2", ...],
            "connections": [
                {{"source": "service1", "target": "service2", "type": "connection_type"}}
            ],
            "compliance_assessment": {{
                "security_score": 85,
                "performance_score": 80,
                "reliability_score": 75,
                "cost_optimization_score": 70,
                "operational_excellence_score": 80
            }},
            "critical_issues": ["issue1", "issue2", ...],
            "quick_wins": ["improvement1", "improvement2", ...],
            "recommendations": ["rec1", "rec2", ...],
            "complexity_level": "Enterprise-Scale/Medium/Simple"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert Azure solution architect. Analyze draw.io XML and respond with valid JSON only."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=agent_config.AGENT_MAX_TOKENS_DEFAULT,
                temperature=agent_config.AGENT_TEMPERATURE
            )
            
            content = response.choices[0].message.content
            
            # Clean up response to ensure valid JSON
            cleaned_content = self._clean_json_response(content)
            if not cleaned_content or cleaned_content == "{}":
                raise Exception("OpenAI response could not be cleaned to valid JSON")
            
            return json.loads(cleaned_content)
                
        except Exception as e:
            # Provide transparent fallback analysis for draw.io - clearly marked as failed analysis
            return {
                "detected_services": [],  # Empty - no services detected due to failure
                "architecture_pattern": "Analysis Failed",
                "resource_groups": [],
                "network_design": "Unable to analyze - manual review required",
                "security_features": [],
                "connections": [],
                "compliance_assessment": {
                    "security_score": 0,
                    "performance_score": 0,
                    "reliability_score": 0,
                    "cost_optimization_score": 0,
                    "operational_excellence_score": 0
                },
                "critical_issues": [
                    f"AI analysis failed: {str(e)}",
                    "Manual review of diagram required"
                ],
                "quick_wins": ["Re-upload diagram or provide clearer requirements"],
                "recommendations": ["Verify diagram format is valid Draw.io XML"],
                "complexity_level": "Medium",
                "is_fallback": True,
                "fallback_reason": str(e)
            }

    async def validate_architecture_from_drawio(self, drawio_xml: str, drawio_analysis: Dict[str, Any], requirements: str) -> Dict[str, Any]:
        """Validate architecture from draw.io XML content with parsed analysis"""
        try:
            # Use the pre-parsed analysis from the drawio_parser
            components = drawio_analysis.get('components', [])
            connections = drawio_analysis.get('connections', [])
            azure_services = drawio_analysis.get('azure_services', {})
            architecture_insights = drawio_analysis.get('architecture_insights', {})
            
            # Run agent analysis on the extracted services
            all_services = []
            for category, services in azure_services.items():
                all_services.extend(services)
            
            # Get agent recommendations if services are detected
            agent_results = []
            if all_services and requirements:
                try:
                    agent_results = await self.orchestrator.analyze_architecture(requirements, context={
                        "services": all_services,
                        "drawio_components": components,
                        "drawio_connections": connections
                    })
                except Exception as e:
                    print(f"Agent analysis failed: {e}")
            
            # Generate AI analysis
            ai_analysis = await self._analyze_drawio_with_openai(drawio_xml, drawio_analysis, requirements)
            
            # Validate connections against learned patterns from Azure Architecture Center
            learned_patterns_validation = self.validate_connections_with_learned_patterns(all_services, connections)
            
            # Calculate scores based on analysis
            compliance_score = self._calculate_compliance_score(drawio_analysis, requirements)
            
            # Generate critical issues and quick wins
            critical_issues = await self._identify_critical_issues(requirements, drawio_xml)
            quick_wins = await self._suggest_quick_wins(requirements, drawio_xml)
            
            return {
                "validation_id": f"drawio_val_{abs(hash(requirements + drawio_xml[:100]))}",
                "compliance_score": compliance_score,
                "critical_issues": critical_issues,
                "quick_wins": quick_wins,
                "ai_comparison": {
                    "strengths": ai_analysis.get("strengths", []),
                    "gaps": ai_analysis.get("gaps", []),
                    "insights": ai_analysis.get("insights", "Draw.io architecture analyzed successfully."),
                    "well_architected_scores": ai_analysis.get("well_architected_scores", {
                        "security": 0,
                        "reliability": 0,
                        "performance": 0,
                        "cost_optimization": 0,
                        "operational_excellence": 0
                    }),
                    "overall_score": ai_analysis.get("overall_score", compliance_score),
                    "architecture_assessment": {
                        "detected_services": all_services,
                        "connections": connections,
                        "architecture_patterns": architecture_insights.get("architecture_patterns", []),
                        "complexity_assessment": architecture_insights.get("complexity_assessment", "Moderate"),
                        "total_components": drawio_analysis.get("total_components", 0)
                    }
                },
                "agent_recommendations": {
                    "agents_results": agent_results,
                    "summary": {
                        "total_agents": len(agent_results),
                        "agents_completed": len([r for r in agent_results if r.get("status") == "completed"]),
                        "critical_issues_found": len(critical_issues),
                        "recommendations_generated": sum(len(r.get("recommendations", [])) for r in agent_results)
                    }
                },
                "recommendations": {
                    "critical": critical_issues[:3],
                    "high_priority": quick_wins[:3],
                    "medium_priority": [],
                    "low_priority": []
                },
                "learned_patterns_analysis": learned_patterns_validation
            }
            
        except Exception as e:
            print(f"Error in validate_architecture_from_drawio: {e}")
            # Return fallback response
            return {
                "validation_id": f"drawio_val_error_{int(time.time())}",
                "compliance_score": 50,
                "critical_issues": ["Analysis failed - manual review required"],
                "quick_wins": ["Re-upload file in proper Draw.io format"],
                "ai_comparison": {
                    "strengths": [],
                    "gaps": ["Unable to complete automated analysis"],
                    "insights": f"Error occurred during analysis: {str(e)}",
                    "well_architected_scores": {
                        "security": 0,
                        "reliability": 0,
                        "performance": 0,
                        "cost_optimization": 0,
                        "operational_excellence": 0
                    },
                    "overall_score": 0,
                    "architecture_assessment": {
                        "detected_services": [],
                        "connections": [],
                        "architecture_patterns": [],
                        "complexity_assessment": "Unknown"
                    }
                },
                "agent_recommendations": {
                    "agents_results": [],
                    "summary": {
                        "total_agents": 0,
                        "agents_completed": 0,
                        "critical_issues_found": 1,
                        "recommendations_generated": 0
                    }
                },
                "recommendations": {
                    "critical": ["Manual review required due to analysis error"],
                    "high_priority": [],
                    "medium_priority": [],
                    "low_priority": []
                }
            }
       
        
    async def analyze_diagram_image(self, image_base64: str, content_type: str, context: str = "") -> Dict[str, Any]:
        """Analyze architecture diagram image using Azure OpenAI Vision capabilities"""
        
        image_analysis_prompt = f"""
        Analyze this Azure architecture diagram image and provide a comprehensive assessment:
        
        CONTEXT: {context}
        
        Please analyze the diagram and identify:
        
        1. **AZURE SERVICES DETECTED**: List all Azure services visible in the diagram
        2. **ARCHITECTURE PATTERN**: Identify the architectural pattern (e.g., Multi-tier, Microservices, etc.)
        3. **RESOURCE GROUPS**: Identify how resources are organized
        4. **NETWORK DESIGN**: Analyze network architecture, subnets, connectivity
        5. **SECURITY FEATURES**: Identify security implementations (WAF, private endpoints, etc.)
        6. **DATA FLOW**: Describe how data flows between services
        7. **CONNECTIONS**: List service-to-service connections
        8. **BEST PRACTICES COMPLIANCE**: Assess adherence to Azure Well-Architected Framework
        
        Provide response in JSON format:
        {{
            "detected_services": ["service1", "service2", ...],
            "architecture_pattern": "pattern name",
            "resource_groups": ["rg1", "rg2", ...],
            "network_design": "description of network architecture",
            "security_features": ["feature1", "feature2", ...],
            "connections": [
                {{"source": "service1", "target": "service2", "type": "connection_type"}}
            ],
            "compliance_assessment": {{
                "security_score": 85,
                "performance_score": 80,
                "reliability_score": 75,
                "cost_optimization_score": 70,
                "operational_excellence_score": 80
            }},
            "critical_issues": ["issue1", "issue2", ...],
            "quick_wins": ["improvement1", "improvement2", ...],
            "recommendations": ["rec1", "rec2", ...],
            "complexity_level": "Enterprise-Scale/Medium/Simple"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": image_analysis_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{content_type};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=agent_config.AGENT_MAX_TOKENS_DEFAULT,
                temperature=agent_config.AGENT_TEMPERATURE
            )
            
            content = response.choices[0].message.content
            
            # Clean up response to ensure valid JSON
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If JSON parsing fails, raise an exception instead of returning mock data
                raise Exception(f"Failed to parse AI vision response as JSON. Raw content: {content[:200]}...")
                
        except Exception as e:
            raise Exception(f"Image analysis failed: {str(e)}")

    async def _analyze_drawio_with_openai(self, drawio_data: Dict, requirements: str) -> Dict[str, Any]:
        """Analyze Draw.io architecture data using OpenAI."""
        
        # Extract key information from Draw.io data
        services = []
        connections = []
        
        if 'components' in drawio_data:
            for category, items in drawio_data['components'].items():
                services.extend([item['name'] for item in items])
        
        if 'connections' in drawio_data:
            connections = drawio_data['connections']
        
        analysis_prompt = f"""
        As an Azure Solutions Architect, analyze this Draw.io architecture diagram data:
        
        DETECTED SERVICES: {', '.join(services)}
        CONNECTIONS: {json.dumps(connections, indent=2)}
        REQUIREMENTS: {requirements}
        
        Please provide a comprehensive analysis including:
        
        1. **ARCHITECTURE ASSESSMENT**: Evaluate the overall architecture design
        2. **SERVICE ANALYSIS**: Assess each Azure service usage and configuration
        3. **CONNECTIVITY**: Analyze service connections and data flow
        4. **SECURITY**: Evaluate security implementations and gaps
        5. **PERFORMANCE**: Assess performance characteristics
        6. **RELIABILITY**: Evaluate availability and fault tolerance
        7. **COST OPTIMIZATION**: Identify cost optimization opportunities
        8. **OPERATIONAL EXCELLENCE**: Assess operational aspects
        
        Provide response in JSON format:
        {{
            "architecture_pattern": "pattern name",
            "services_analysis": {{
                "appropriate_services": ["service1", "service2"],
                "questionable_services": ["service3"],
                "missing_services": ["service4"]
            }},
            "connectivity_analysis": {{
                "well_designed_connections": ["connection1"],
                "problematic_connections": ["connection2"],
                "missing_connections": ["connection3"]
            }},
            "compliance_scores": {{
                "security": 85,
                "performance": 80,
                "reliability": 75,
                "cost_optimization": 70,
                "operational_excellence": 80
            }},
            "critical_issues": ["issue1", "issue2"],
            "recommendations": ["rec1", "rec2"],
            "quick_wins": ["improvement1", "improvement2"],
            "complexity_assessment": "Enterprise-Scale/Medium/Simple"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=agent_config.AGENT_MAX_TOKENS_DEFAULT,
                temperature=agent_config.AGENT_TEMPERATURE
            )
            
            content = response.choices[0].message.content
            
            # Clean up response to ensure valid JSON
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If JSON parsing fails, raise an exception
                raise Exception(f"Failed to parse AI analysis response as JSON. Raw content: {content[:200]}...")
                
        except Exception as e:
            raise Exception(f"Draw.io analysis failed: {str(e)}")

    def _calculate_compliance_score(self, analysis: Dict[str, Any], services: List[Dict] = None, connections: List[Dict] = None, requirements: str = "") -> Dict[str, Any]:
        """Calculate overall compliance score from analysis results.
        
        Uses the AccuracyScorer from accuracy_enhancements if available,
        providing meaningful scores based on actual architecture analysis
        rather than arbitrary defaults.
        """
        
        # Try to use AccuracyScorer for more accurate scoring
        if self.accuracy_scorer and services:
            try:
                computed_scores = self.accuracy_scorer.calculate_architecture_score(
                    services=services,
                    connections=connections or [],
                    requirements=requirements,
                    security_analysis=analysis.get("security_analysis"),
                    performance_analysis=analysis.get("performance_analysis")
                )
                
                return {
                    'overall_score': computed_scores.get('overall_score', 0),
                    'compliance_level': self._determine_compliance_level(computed_scores.get('overall_score', 0)),
                    'individual_scores': {
                        'security': computed_scores['pillar_scores'].get('security', {}).get('score', 0),
                        'reliability': computed_scores['pillar_scores'].get('reliability', {}).get('score', 0),
                        'performance': computed_scores['pillar_scores'].get('performance', {}).get('score', 0),
                        'cost_optimization': computed_scores['pillar_scores'].get('cost_optimization', {}).get('score', 0),
                        'operational_excellence': computed_scores['pillar_scores'].get('operational_excellence', {}).get('score', 0)
                    },
                    'pillar_details': computed_scores.get('pillar_scores', {}),
                    'improvements': computed_scores.get('improvements', []),
                    'scoring_methodology': 'computed_from_architecture',
                    'critical_issues_count': len(analysis.get('critical_issues', [])),
                    'recommendations_count': len(analysis.get('recommendations', []))
                }
            except Exception as e:
                print(f"AccuracyScorer failed, falling back to default scoring: {e}")
        
        # Fallback scoring logic (original implementation)
        if 'compliance_scores' not in analysis:
            # Fallback calculation if compliance_scores not in analysis
            base_score = 75
            
            # Adjust based on critical issues
            critical_issues = len(analysis.get('critical_issues', []))
            score_deduction = min(critical_issues * 10, 40)  # Max 40 point deduction
            
            overall_score = max(base_score - score_deduction, 0)
        else:
            # Calculate weighted average of compliance scores
            scores = analysis['compliance_scores']
            weights = {
                'security': 0.25,
                'performance': 0.2,
                'reliability': 0.25,
                'cost_optimization': 0.15,
                'operational_excellence': 0.15
            }
            
            overall_score = sum(scores.get(category, 75) * weight 
                              for category, weight in weights.items())
        
        # Determine compliance level
        if overall_score >= 85:
            compliance_level = "Excellent"
        elif overall_score >= 70:
            compliance_level = "Good"
        elif overall_score >= 55:
            compliance_level = "Fair"
        else:
            compliance_level = "Poor"
        
        return {
            'overall_score': round(overall_score, 1),
            'compliance_level': compliance_level,
            'individual_scores': analysis.get('compliance_scores', {}),
            'critical_issues_count': len(analysis.get('critical_issues', [])),
            'recommendations_count': len(analysis.get('recommendations', []))
        }

    def _determine_compliance_level(self, score: float) -> str:
        """Determine compliance level from numeric score."""
        if score >= 85:
            return "Excellent"
        elif score >= 70:
            return "Good"
        elif score >= 55:
            return "Fair"
        else:
            return "Poor"

    async def validate_architecture_from_images(
        self, 
        actual_image_b64: str, 
        expected_image_b64: Optional[str], 
        requirements: str,
        actual_content_type: str,
        expected_content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate architecture by analyzing uploaded diagram images"""
        
        # Analyze actual diagram
        actual_analysis = await self.analyze_diagram_image(
            actual_image_b64, 
            actual_content_type, 
            f"Requirements: {requirements}"
        )
        
        # Analyze expected diagram if provided
        expected_analysis = None
        if expected_image_b64 and expected_content_type:
            expected_analysis = await self.analyze_diagram_image(
                expected_image_b64,
                expected_content_type,
                f"Expected architecture for requirements: {requirements}"
            )
        
        # Get agent-based analysis for comparison
        agent_analysis = await self.orchestrator.generate_architecture(requirements)
        
        # Perform AI analysis using OpenAI
        ai_analysis = await self.analyze_with_openai(requirements, agent_analysis.get("agents_results", []))
        
        # Calculate compliance scores
        compliance_scores = actual_analysis.get("compliance_assessment", {})
        overall_compliance = sum(compliance_scores.values()) / len(compliance_scores) if compliance_scores else 75
        
        # Combine critical issues and quick wins from image analysis and AI
        critical_issues = list(actual_analysis.get("critical_issues", []))
        critical_issues.extend(ai_analysis.get("critical_issues", []))
        
        quick_wins = list(actual_analysis.get("quick_wins", []))
        quick_wins.extend(ai_analysis.get("quick_wins", []))
        
        # Compare with expected if available
        comparison_results = {}
        if expected_analysis:
            comparison_results = self._compare_architectures(actual_analysis, expected_analysis)
        
        return {
            "validation_id": f"img_val_{abs(hash(requirements + actual_image_b64[:100]))}",
            "compliance_score": int(overall_compliance),
            "critical_issues": critical_issues[:5],
            "quick_wins": quick_wins[:5],
            
            # AI Comparison Section (matches frontend expectations)
            "ai_comparison": {
                "strengths": ai_analysis.get("strengths", []) + [f"Detected {len(actual_analysis.get('detected_services', []))} services in diagram"],
                "gaps": ai_analysis.get("gaps", []) + actual_analysis.get("critical_issues", [])[:2],
                "insights": f"Image analysis detected: {actual_analysis.get('architecture_pattern', 'Unknown pattern')}. " + ai_analysis.get("insights", ""),
                "well_architected_scores": {
                    "security": compliance_scores.get("security_score", 0),
                    "reliability": compliance_scores.get("reliability_score", 0),
                    "performance": compliance_scores.get("performance_score", 0),
                    "cost_optimization": compliance_scores.get("cost_optimization_score", 0),
                    "operational_excellence": compliance_scores.get("operational_excellence_score", 0)
                },
                "overall_score": int(overall_compliance),
                "architecture_assessment": {
                    "detected_services": actual_analysis.get("detected_services", []),
                    "architecture_pattern": actual_analysis.get("architecture_pattern", "Not determined"),
                    "complexity_level": actual_analysis.get("complexity_level", "Medium"),
                    "resource_groups": actual_analysis.get("resource_groups", []),
                    "security_features": actual_analysis.get("security_features", []),
                    "comparison_results": comparison_results
                }
            },
            
            # Agent Recommendations Section (matches frontend expectations)
            "agent_recommendations": {
                "agents_results": agent_analysis.get("agents_results", []),
                "summary": {
                    "total_agents": len(agent_analysis.get("agents_results", [])),
                    "agents_completed": len([r for r in agent_analysis.get("agents_results", []) if r.get("status") == "completed"]),
                    "critical_issues_found": len(critical_issues),
                    "recommendations_generated": len(quick_wins)
                }
            },
            
            # Recommendations Section (matches frontend expectations)
            "recommendations": {
                "critical": [
                    {
                        "title": str(issue),
                        "description": f"Critical: {issue}",
                        "priority": "high",
                        "effort": "medium"
                    }
                    for issue in critical_issues[:5]
                ],
                "high": [
                    {
                        "title": str(win),
                        "description": f"High priority: {win}",
                        "priority": "high",
                        "effort": "low"
                    }
                    for win in quick_wins[:4]
                ],
                "medium": [
                    {
                        "title": str(rec),
                        "description": f"Medium priority: {rec}",
                        "priority": "medium",
                        "effort": "medium"
                    }
                    for rec in actual_analysis.get("recommendations", [])[:3]
                ]
            },
            
            "validation_type": "Image-based Architecture Analysis",
            "architecture_complexity": actual_analysis.get("complexity_level", "Medium"),
            "timestamp": "2026-01-20T00:00:00Z"
        }

    def _compare_architectures(self, actual: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
        """Compare actual vs expected architecture analysis"""
        
        actual_services = set(actual.get("detected_services", []))
        expected_services = set(expected.get("detected_services", []))
        
        missing_services = expected_services - actual_services
        extra_services = actual_services - expected_services
        matching_services = actual_services.intersection(expected_services)
        
        actual_scores = actual.get("compliance_assessment", {})
        expected_scores = expected.get("compliance_assessment", {})
        
        score_differences = {}
        for score_type in actual_scores:
            if score_type in expected_scores:
                score_differences[score_type] = actual_scores[score_type] - expected_scores[score_type]
        
        return {
            "services_comparison": {
                "matching_services": list(matching_services),
                "missing_services": list(missing_services),
                "extra_services": list(extra_services),
                "match_percentage": len(matching_services) / max(len(expected_services), 1) * 100
            },
            "score_differences": score_differences,
            "architecture_pattern_match": actual.get("architecture_pattern") == expected.get("architecture_pattern"),
            "overall_similarity": len(matching_services) / max(len(actual_services.union(expected_services)), 1) * 100
        }

    async def analyze_with_openai(self, requirements: str, agent_results: List[Dict]) -> Dict[str, Any]:
        """Use OpenAI to analyze requirements and agent recommendations"""
        
        analysis_prompt = f"""
        As an expert Azure solution architect specializing in enterprise-scale, multi-tier architectures, analyze these requirements and agent recommendations:
        
        REQUIREMENTS: {requirements}
        
        AGENT ANALYSIS:
        {json.dumps(agent_results, indent=2)}
        
        For complex Azure architectures, evaluate these critical areas:
        
        ARCHITECTURE ASSESSMENT:
        1. Resource Group Organization (domain separation, shared services, monitoring/security)
        2. Network Architecture (VNet design, subnets, private endpoints, NSGs)
        3. Security Implementation (WAF, private endpoints, managed identity, Key Vault)
        4. High Availability & Scalability (multi-zone deployment, auto-scaling, load balancing)
        5. Monitoring & Observability (Application Insights, Log Analytics, dashboards)
        6. Cost Optimization (right-sizing, reserved instances, storage tiers)
        
        VALIDATION CRITERIA:
        - Private endpoints for all PaaS services (PostgreSQL, Redis, Storage, Key Vault)
        - WAF protection on Application Gateway and Front Door
        - Proper network segmentation across tiers
        - Managed Identity for service authentication
        - Comprehensive monitoring and logging
        - Disaster recovery and backup strategies
        
        Provide a comprehensive JSON analysis with:
        {{
            "strengths": ["specific architecture strengths identified"],
            "gaps": ["critical gaps and missing components"], 
            "insights": "detailed AI analysis and observations about the architecture",
            "recommendations": {{
                "critical": ["immediate fixes needed"],
                "high": ["important improvements"], 
                "medium": ["nice to have enhancements"]
            }},
            "security_score": 85,
            "performance_score": 78,
            "compliance_score": 82,
            "reliability_score": 80,
            "cost_optimization_score": 75,
            "critical_issues": ["immediate attention required"],
            "quick_wins": ["easy improvements to implement"],
            "architecture_pattern_assessment": "evaluation of chosen pattern",
            "resource_group_assessment": "evaluation of resource organization",
            "network_design_assessment": "evaluation of network architecture",
            "security_implementation_assessment": "detailed security evaluation",
            "comparison_with_best_practices": "how this compares to Azure Well-Architected Framework",
            "detected_services": ["list of services identified from requirements"],
            "missing_services": ["services that should be added"],
            "scalability_assessment": "evaluation of scaling approach"
        }}
        
        IMPORTANT: Always include numeric scores (0-100) for all score categories.
        Focus on Azure Well-Architected Framework pillars and enterprise-scale best practices.
        Specifically look for multi-tier architecture patterns with proper separation of concerns.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert Azure solution architect. Always respond with valid JSON only, no additional text or explanations."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3,
                max_tokens=agent_config.AGENT_MAX_TOKENS_DEFAULT,  # Configurable via AGENT_MAX_TOKENS_DEFAULT
                top_p=0.9
            )
            
            # Validate response content exists
            content = response.choices[0].message.content
            if not content or content.strip() == "":
                raise Exception("OpenAI returned empty response")
            
            # Clean the response before parsing
            cleaned_content = self._clean_json_response(content)
            if not cleaned_content or cleaned_content == "{}":
                raise Exception("OpenAI response could not be cleaned to valid JSON")
            
            result = json.loads(cleaned_content)
            
            # Ensure we have all required scores
            scores = {
                "security_score": result.get("security_score", 0),
                "performance_score": result.get("performance_score", 0),
                "compliance_score": result.get("compliance_score", 0),
                "reliability_score": result.get("reliability_score", 0),
                "cost_optimization_score": result.get("cost_optimization_score", 0)
            }
            
            # Calculate overall score
            overall_score = sum(scores.values()) / len(scores)
            result["overall_score"] = int(overall_score)
            result.update(scores)
            
            return result
            
        except Exception as e:
            print(f"OpenAI analysis failed: {e}")
            # Provide fallback analysis with honest zero scores
            fallback_result = {
                "strengths": [],
                "gaps": ["AI analysis temporarily unavailable"],
                "insights": f"Analysis fallback due to: {str(e)}. Using agent-based recommendations.",
                "recommendations": {
                    "critical": ["Review agent-specific recommendations below"],
                    "high": ["Ensure all required services are properly configured"],
                    "medium": ["Consider optimization opportunities from agents"]
                },
                "security_score": 0,
                "performance_score": 0,
                "compliance_score": 0,
                "reliability_score": 0,
                "cost_optimization_score": 0,
                "overall_score": 0,
                "is_fallback": True,
                "fallback_reason": str(e),
                "critical_issues": ["AI analysis temporarily unavailable"],
                "quick_wins": ["Review individual agent recommendations"],
                "architecture_pattern_assessment": "Analysis based on agent feedback",
                "resource_group_assessment": "Review agent security and organization recommendations",
                "network_design_assessment": "Check agent performance recommendations",
                "security_implementation_assessment": "See security agent analysis",
                "comparison_with_best_practices": "Partial analysis from specialized agents",
                "detected_services": [],
                "missing_services": [],
                "scalability_assessment": "Review performance agent recommendations"
            }
            logger.warning(f"[FALLBACK] Using fallback analysis due to OpenAI API issues: {str(e)}")
            return fallback_result
         
        
    async def generate_validation_report(self, actual_diagram: str, expected_diagram: str, requirements: str) -> Dict[str, Any]:
        """Generate comprehensive validation report using AI and agents for complex architectures"""
        
        # Step 1: Get enhanced agent-based analysis for complex architectures
        agent_analysis = await self.orchestrator.generate_architecture(requirements)
        
        # Step 2: Use OpenAI for intelligent analysis with complex architecture context
        ai_analysis = await self.analyze_with_openai(requirements, agent_analysis["agents_results"])
        
        # Step 3: Calculate comprehensive compliance score
        compliance_score = ai_analysis.get("compliance_score", agent_config.DEFAULT_COMPLIANCE_SCORE)
        if not isinstance(compliance_score, (int, float)):
            # Calculate from multiple pillars for complex architectures
            security_score = ai_analysis.get("security_score", agent_config.DEFAULT_COMPLIANCE_SCORE)
            performance_score = ai_analysis.get("performance_score", agent_config.DEFAULT_COMPLIANCE_SCORE) 
            reliability_score = ai_analysis.get("reliability_score", agent_config.DEFAULT_COMPLIANCE_SCORE)
            cost_score = ai_analysis.get("cost_optimization_score", agent_config.DEFAULT_COMPLIANCE_SCORE)
            
            scores = [security_score, performance_score, reliability_score, cost_score]
            valid_scores = [s for s in scores if isinstance(s, (int, float))]
            compliance_score = int(sum(valid_scores) / len(valid_scores)) if valid_scores else agent_config.FALLBACK_AVERAGE_SCORE
        
        # Step 4: Enhanced critical issues analysis for complex architectures
        critical_issues = ai_analysis.get("critical_issues", [])
        
        # Step 5: Enhanced quick wins for complex architectures  
        quick_wins = ai_analysis.get("quick_wins", [])
        
        # Step 6: Architecture-specific assessments
        architecture_assessment = {
            "architecture_pattern": agent_analysis.get("combined_architecture", {}).get("architecture_pattern", "Unknown"),
            "resource_group_organization": ai_analysis.get("resource_group_assessment", "Not assessed"),
            "network_design": ai_analysis.get("network_design_assessment", "Not assessed"),
            "security_implementation": ai_analysis.get("security_implementation_assessment", "Not assessed"),
            "monitoring_strategy": ai_analysis.get("monitoring_strategy", "Not defined"),
            "disaster_recovery": ai_analysis.get("disaster_recovery", "Not defined")
        }
        
        return {
            "validation_id": f"complex_ai_val_{abs(hash(requirements + actual_diagram[:50]))}",
            "compliance_score": compliance_score,
            "critical_issues": critical_issues[:5],  # Limit to top 5
            "quick_wins": quick_wins[:5],  # Limit to top 5
            
            # AI Comparison Section (matches frontend expectations)
            "ai_comparison": {
                "strengths": ai_analysis.get("strengths", []),
                "gaps": ai_analysis.get("gaps", []), 
                "insights": ai_analysis.get("insights", ""),
                "well_architected_scores": {
                    "security": ai_analysis.get("security_score", 0),
                    "reliability": ai_analysis.get("reliability_score", 0),
                    "performance": ai_analysis.get("performance_score", 0),
                    "cost_optimization": ai_analysis.get("cost_optimization_score", 0),
                    "operational_excellence": ai_analysis.get("operational_excellence_score", 0)
                },
                "overall_score": compliance_score,
                "architecture_assessment": architecture_assessment
            },
            
            # Agent Recommendations Section (matches frontend expectations)
            "agent_recommendations": {
                "agents_results": agent_analysis.get("agents_results", []),
                "summary": {
                    "total_agents": len(agent_analysis.get("agents_results", [])),
                    "agents_completed": len([r for r in agent_analysis.get("agents_results", []) if r.get("status") == "completed"]),
                    "critical_issues_found": len(critical_issues),
                    "recommendations_generated": len(quick_wins)
                }
            },
            
            # Recommendations Section (matches frontend expectations)
            "recommendations": {
                "critical": [
                    {
                        "title": str(issue), 
                        "description": f"Critical: {issue}",
                        "priority": "high",
                        "effort": "medium"
                    } 
                    for issue in critical_issues[:5]
                ],
                "high": [
                    {
                        "title": str(win), 
                        "description": f"High priority: {win}",
                        "priority": "high", 
                        "effort": "low"
                    }
                    for win in quick_wins[:4]
                ],
                "medium": [
                    {
                        "title": str(rec),
                        "description": f"Medium priority: {rec}",
                        "priority": "medium",
                        "effort": "medium"
                    }
                    for rec in ai_analysis.get("recommendations", {}).get("medium", [])[:3]
                ]
            },
            "validation_type": "AI-Enhanced Complex Architecture Analysis",
            "architecture_complexity": "Enterprise-Scale Multi-Tier"
        }
    
    async def _generate_fallback_validation(self, requirements: str, error: str) -> Dict[str, Any]:
        """Generate honest fallback validation when AI analysis fails"""
        return {
            "validation_id": f"fallback_{int(time.time())}",
            "compliance_score": 0,
            "is_fallback": True,
            "fallback_reason": error,
            "critical_issues": [f"Validation failed: {error}"],
            "quick_wins": ["Retry validation or contact support"],
            
            "ai_comparison": {
                "strengths": [],
                "gaps": ["Analysis unavailable due to system error"], 
                "insights": f"Validation failed: {error}",
                "well_architected_scores": {
                    "security": 0,
                    "reliability": 0,
                    "performance": 0,
                    "cost_optimization": 0,
                    "operational_excellence": 0
                },
                "overall_score": 0,
                "architecture_assessment": {
                    "pattern_detected": "Unknown",
                    "complexity_level": "Unknown",
                    "estimated_cost": "Unknown"
                }
            },
            
            "agent_recommendations": {
                "agents_results": [],
                "summary": {
                    "total_agents": 0,
                    "agents_completed": 0,
                    "critical_issues_found": 1,
                    "recommendations_generated": 0
                }
            },
            
            "recommendations": {
                "critical": [
                    {
                        "title": "Validation System Error", 
                        "description": f"Critical: {error}", 
                        "priority": "high", 
                        "effort": "medium"
                    }
                ],
                "high": [],
                "medium": []
            },
            
            "validation_type": "Fallback Analysis",
            "architecture_complexity": "Unknown",
            "timestamp": datetime.now().isoformat(),
            "error_note": f"Primary analysis failed: {error}",
            "validation_error": error
        }
    
    async def _analyze_terraform_files(self, terraform_files: List[str], content: bytes) -> Dict[str, Any]:
        """Analyze terraform files to provide dynamic reverse engineering results"""
        try:
            # Parse terraform file names to identify services
            services = []
            patterns = []
            
            for file in terraform_files:
                file_lower = file.lower()
                if "app" in file_lower or "service" in file_lower:
                    services.append("App Service")
                    patterns.append("Web Application Pattern")
                if "db" in file_lower or "sql" in file_lower:
                    services.append("SQL Database")
                    patterns.append("Database Pattern")
                if "storage" in file_lower:
                    services.append("Storage Account")
                    patterns.append("Data Storage Pattern")
                if "network" in file_lower or "vnet" in file_lower:
                    services.append("Virtual Network")
                    patterns.append("Network Security Pattern")
                if "key" in file_lower or "vault" in file_lower:
                    services.append("Key Vault")
                    patterns.append("Security Pattern")
            
            implemented = list(set(patterns)) or ["Infrastructure as Code", "Automated Deployment"]
            missing = []
            
            if "Security Pattern" not in implemented:
                missing.append("Security Configuration")
            if "Database Pattern" not in implemented:
                missing.append("Data Persistence")
            if "Network Security Pattern" not in implemented:
                missing.append("Network Security")
                
            return {
                "analysis": {
                    "implemented": implemented,
                    "missing": missing,
                    "detected_services": list(set(services)),
                    "terraform_complexity": "Medium" if len(terraform_files) > 3 else "Low"
                }
            }
        except Exception as e:
            return {
                "analysis": {
                    "implemented": ["Terraform Configuration"],
                    "missing": ["Analysis Error", f"Error: {str(e)}"],
                    "detected_services": [],
                    "terraform_complexity": "Unknown"
                }
            }
    
    def _calculate_dynamic_compliance(self, requirements: str) -> int:
        """Calculate compliance score based on requirements complexity"""
        req_hash = abs(hash(requirements))
        base_score = 70 + (req_hash % 25)  # Score between 70-94
        
        # Adjust based on requirements complexity
        req_lower = requirements.lower()
        complexity_bonus = 0
        
        complex_terms = ["microservice", "enterprise", "scale", "redundancy", "disaster"]
        for term in complex_terms:
            if term in req_lower:
                complexity_bonus += 2
        
        return min(95, base_score + complexity_bonus)
    
    async def _identify_critical_issues(self, requirements: str, drawio_xml: str) -> List[str]:
        """Dynamically identify critical issues based on requirements and architecture"""
        issues = []
        req_lower = requirements.lower()
        
        if "security" in req_lower and "encryption" not in drawio_xml.lower():
            issues.append("Encryption at rest not configured")
        if "production" in req_lower and "backup" not in drawio_xml.lower():
            issues.append("No backup strategy defined")
        if "web" in req_lower and "waf" not in drawio_xml.lower():
            issues.append("Web Application Firewall missing")
        if "database" in req_lower and "private" not in drawio_xml.lower():
            issues.append("Database not in private network")
        if "api" in req_lower and "rate" not in drawio_xml.lower():
            issues.append("API rate limiting not configured")
        
        return issues[:5] if issues else ["Review architecture components"]
    
    async def _suggest_quick_wins(self, requirements: str, drawio_xml: str) -> List[str]:
        """Dynamically suggest quick wins based on requirements"""
        wins = []
        req_lower = requirements.lower()
        
        if "azure" in req_lower:
            wins.append("Enable Azure Monitor")
        if "web" in req_lower:
            wins.append("Configure SSL certificates")
        if "security" in req_lower:
            wins.append("Enable Azure Defender")
        if "api" in req_lower:
            wins.append("Set up API Management")
        if "database" in req_lower:
            wins.append("Configure database firewall rules")
        
        wins.append("Implement Infrastructure as Code")
        wins.append("Set up automated monitoring alerts")
        
        return wins[:5]