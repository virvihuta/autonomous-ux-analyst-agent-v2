"""Pydantic Models for Website Reverse-Engineering Blueprint"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DataModelAttribute(BaseModel):
    name: str
    inferred_type: str = "string"
    example_value: Optional[Any] = None


class InferredDataModel(BaseModel):
    entity: str = Field(..., description="Name of the entity (e.g., User, Product)")
    attributes: List[str] = Field(default_factory=list)
    detailed_attributes: List[DataModelAttribute] = Field(default_factory=list)
    source: str = Field(default="ui", description="Where this was inferred from: ui, api, form")


class NetworkIntercept(BaseModel):
    url: str
    method: str = "GET"
    status_code: Optional[int] = None
    payload_structure: Optional[Dict[str, Any]] = None
    response_structure: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None


class PageCluster(BaseModel):
    cluster_id: str = Field(..., description="SHA256 hash of the structural DOM")
    page_type: str = Field(default="Unknown")
    representative_url: str = Field(...)
    total_pages_in_cluster: int = Field(default=1)
    sample_urls: List[str] = Field(default_factory=list)
    
    inferred_data_models: List[InferredDataModel] = Field(default_factory=list)
    network_intercepts: List[NetworkIntercept] = Field(default_factory=list)
    
    forms_found: int = 0
    buttons_found: int = 0
    inputs_found: int = 0
    
    cleaned_dom_tokens: int = Field(default=0)
    raw_dom_size: int = Field(default=0)


class RebuildBlueprint(BaseModel):
    project_name: str
    base_url: str
    total_pages_crawled: int = 0
    unique_clusters_found: int = 0
    total_tokens_saved: int = Field(default=0)
    
    clusters: List[PageCluster] = Field(default_factory=list)
    global_data_models: List[InferredDataModel] = Field(default_factory=list)
    statistics: Dict[str, Any] = Field(default_factory=dict)
