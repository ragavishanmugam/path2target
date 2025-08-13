"""
LLM-powered reasoning for biomedical data model refinement.
Provides intelligent analysis and enhancement of YAML data models.
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import yaml

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class ModelAnalysis:
    """Results of LLM analysis of a data model."""
    suggestions: List[str]
    missing_entities: List[str]
    missing_relationships: List[str]
    ontology_recommendations: List[str]
    property_enhancements: Dict[str, List[str]]
    reasoning: str
    confidence_score: float


class LLMModelReasoner:
    """LLM-powered reasoning engine for biomedical data models."""
    
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the LLM client based on provider."""
        if self.provider == "openai" and OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = openai.OpenAI(api_key=api_key)
        elif self.provider == "anthropic" and ANTHROPIC_AVAILABLE:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.client = anthropic.Anthropic(api_key=api_key)
    
    def is_available(self) -> bool:
        """Check if LLM reasoning is available."""
        return self.client is not None
    
    def analyze_model(self, 
                     yaml_content: str, 
                     entities: List[str], 
                     domain_context: str = "pharmaceutical research") -> ModelAnalysis:
        """
        Analyze a YAML data model and provide intelligent recommendations.
        
        Args:
            yaml_content: The YAML data model content
            entities: List of entities in the model
            domain_context: Domain context for analysis
            
        Returns:
            ModelAnalysis with recommendations
        """
        if not self.is_available():
            return self._fallback_analysis(entities)
        
        prompt = self._create_analysis_prompt(yaml_content, entities, domain_context)
        
        try:
            if self.provider == "openai":
                response = self._query_openai(prompt)
            elif self.provider == "anthropic":
                response = self._query_anthropic(prompt)
            else:
                return self._fallback_analysis(entities)
            
            return self._parse_response(response)
        
        except Exception as e:
            print(f"LLM analysis failed: {e}")
            return self._fallback_analysis(entities)
    
    def refine_yaml_model(self, 
                         yaml_content: str, 
                         analysis: ModelAnalysis) -> str:
        """
        Use LLM to refine and enhance the YAML model based on analysis.
        
        Args:
            yaml_content: Original YAML content
            analysis: Analysis results with recommendations
            
        Returns:
            Enhanced YAML content
        """
        if not self.is_available():
            return yaml_content
        
        prompt = self._create_refinement_prompt(yaml_content, analysis)
        
        try:
            if self.provider == "openai":
                response = self._query_openai(prompt)
            elif self.provider == "anthropic":
                response = self._query_anthropic(prompt)
            else:
                return yaml_content
            
            # Extract YAML from response
            refined_yaml = self._extract_yaml_from_response(response)
            return refined_yaml if refined_yaml else yaml_content
        
        except Exception as e:
            print(f"YAML refinement failed: {e}")
            return yaml_content
    
    def _create_analysis_prompt(self, yaml_content: str, entities: List[str], domain_context: str) -> str:
        """Create prompt for model analysis."""
        return f"""
You are an expert in biomedical data modeling with deep knowledge of ontologies like Biolink, OMOP, GO, CDISC, NCIT, OBI, and EFO.

Analyze this YAML data model for {domain_context}:

ENTITIES: {', '.join(entities)}

YAML MODEL:
```yaml
{yaml_content}
```

Please provide a comprehensive analysis in JSON format with:
1. "suggestions": List of specific improvements
2. "missing_entities": Important entities that should be added given the domain
3. "missing_relationships": Key relationships that are missing
4. "ontology_recommendations": Specific ontology mappings and codes
5. "property_enhancements": Additional properties for each entity type
6. "reasoning": Detailed explanation of your recommendations
7. "confidence_score": Your confidence in the analysis (0.0-1.0)

Focus on:
- Clinical trial standards (CDISC compliance)
- Regulatory requirements
- Biomarker discovery workflows
- Patient/subject data integration
- Drug development lifecycle
- Safety reporting (adverse events)
- Real-world evidence generation

Return only valid JSON.
"""
    
    def _create_refinement_prompt(self, yaml_content: str, analysis: ModelAnalysis) -> str:
        """Create prompt for YAML refinement."""
        return f"""
You are an expert in biomedical data modeling. Refine this YAML data model based on the analysis:

ORIGINAL YAML:
```yaml
{yaml_content}
```

ANALYSIS RESULTS:
- Suggestions: {analysis.suggestions}
- Missing entities: {analysis.missing_entities}
- Missing relationships: {analysis.missing_relationships}
- Ontology recommendations: {analysis.ontology_recommendations}
- Property enhancements: {analysis.property_enhancements}
- Reasoning: {analysis.reasoning}

Please provide an enhanced YAML model that:
1. Adds the recommended missing entities with comprehensive properties
2. Includes the suggested relationships
3. Incorporates ontology mappings and codes
4. Enhances properties with domain-specific attributes
5. Maintains CDISC, OMOP, and Biolink compliance
6. Follows FAIR data principles

Return ONLY the enhanced YAML content, no explanations:
"""
    
    def _query_openai(self, prompt: str) -> str:
        """Query OpenAI API."""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert biomedical data modeling assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        return response.choices[0].message.content
    
    def _query_anthropic(self, prompt: str) -> str:
        """Query Anthropic Claude API."""
        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=2000,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    
    def _parse_response(self, response: str) -> ModelAnalysis:
        """Parse LLM response into ModelAnalysis."""
        try:
            # Try to extract JSON from response
            response_clean = response.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            
            data = json.loads(response_clean)
            
            return ModelAnalysis(
                suggestions=data.get("suggestions", []),
                missing_entities=data.get("missing_entities", []),
                missing_relationships=data.get("missing_relationships", []),
                ontology_recommendations=data.get("ontology_recommendations", []),
                property_enhancements=data.get("property_enhancements", {}),
                reasoning=data.get("reasoning", ""),
                confidence_score=float(data.get("confidence_score", 0.5))
            )
        except Exception as e:
            print(f"Failed to parse LLM response: {e}")
            return self._fallback_analysis([])
    
    def _extract_yaml_from_response(self, response: str) -> Optional[str]:
        """Extract YAML content from LLM response."""
        try:
            # Look for YAML code blocks
            if "```yaml" in response:
                start = response.find("```yaml") + 7
                end = response.find("```", start)
                if end != -1:
                    yaml_content = response[start:end].strip()
                    # Validate YAML
                    yaml.safe_load(yaml_content)
                    return yaml_content
            
            # If no code blocks, try to parse the entire response as YAML
            yaml.safe_load(response)
            return response.strip()
        
        except Exception:
            return None
    
    def _fallback_analysis(self, entities: List[str]) -> ModelAnalysis:
        """Provide fallback analysis when LLM is not available."""
        fallback_suggestions = [
            "Consider adding regulatory compliance properties",
            "Include standardized identifiers for all entities",
            "Add temporal properties for tracking changes",
            "Consider adding data lineage and provenance",
            "Include quality control and validation properties"
        ]
        
        common_missing = [
            "DataQuality", "AuditTrail", "Provenance", "Consent", 
            "Regulation", "Standard", "Version", "Validation"
        ]
        
        return ModelAnalysis(
            suggestions=fallback_suggestions,
            missing_entities=common_missing,
            missing_relationships=[
                "Entity -> validates -> DataQuality",
                "Entity -> trackedBy -> AuditTrail", 
                "Entity -> derivedFrom -> Provenance"
            ],
            ontology_recommendations=[
                "Add NCIT codes for biomedical concepts",
                "Include LOINC codes for measurements",
                "Use SNOMED CT for clinical concepts"
            ],
            property_enhancements={},
            reasoning="Fallback analysis - LLM reasoning not available. Basic recommendations based on biomedical data modeling best practices.",
            confidence_score=0.3
        )


def get_llm_reasoner(provider: str = "auto") -> LLMModelReasoner:
    """
    Get an LLM reasoner instance.
    
    Args:
        provider: "auto", "openai", or "anthropic"
    
    Returns:
        LLMModelReasoner instance
    """
    if provider == "auto":
        # Try OpenAI first, then Anthropic
        if os.getenv("OPENAI_API_KEY"):
            provider = "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        else:
            provider = "openai"  # Will use fallback mode
    
    return LLMModelReasoner(provider=provider)
