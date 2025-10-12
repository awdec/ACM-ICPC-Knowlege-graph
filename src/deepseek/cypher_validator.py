# src/deepseek/cypher_validator.py
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from config.config_manager import ConfigManager, ValidationConfig

# 设置日志
logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """错误类型"""
    SYNTAX = "syntax"
    SECURITY = "security"
    PARAMETER = "parameter"
    COMPLEXITY = "complexity"


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    error_type: Optional[ErrorType] = None
    error_message: str = ""
    warnings: List[str] = None
    complexity_score: int = 0
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class CypherValidator:
    """Cypher 查询验证器"""
    
    # 危险操作关键字
    DANGEROUS_KEYWORDS = {
        # 删除操作
        'DELETE', 'DETACH DELETE',
        # 修改操作
        'SET', 'REMOVE',
        # 创建操作
        'CREATE', 'MERGE',
        # 数据加载
        'LOAD CSV',
        # 过程调用
        'CALL apoc.', 'CALL dbms.',
        # 管理操作
        'DROP', 'CREATE INDEX', 'CREATE CONSTRAINT'
    }
    
    # 允许的操作关键字
    ALLOWED_KEYWORDS = {
        'MATCH', 'OPTIONAL MATCH', 'WHERE', 'RETURN', 'WITH',
        'ORDER BY', 'LIMIT', 'SKIP', 'DISTINCT', 'COUNT',
        'SUM', 'AVG', 'MIN', 'MAX', 'UNWIND',
        'toLower', 'toUpper', 'substring', 'size', 'length'
    }
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """初始化验证器
        
        Args:
            config: 验证配置，如果为 None 则从 ConfigManager 获取
        """
        self.config = config or ConfigManager().get_validation_config()
    
    def validate(self, cypher: str, parameters: Dict[str, Any] = None) -> ValidationResult:
        """验证 Cypher 查询
        
        Args:
            cypher: Cypher 查询语句
            parameters: 查询参数
            
        Returns:
            ValidationResult 对象
        """
        if parameters is None:
            parameters = {}
        
        # 检查是否为空
        if not cypher or not cypher.strip():
            return ValidationResult(
                is_valid=False,
                error_type=ErrorType.SYNTAX,
                error_message="Empty Cypher query"
            )
        
        cypher = cypher.strip()
        warnings = []
        
        # 1. 安全性检查
        if self.config.enable_security_check:
            security_result = self._check_security(cypher)
            if not security_result[0]:
                return ValidationResult(
                    is_valid=False,
                    error_type=ErrorType.SECURITY,
                    error_message=security_result[1]
                )
        
        # 2. 语法检查
        if self.config.enable_syntax_check:
            syntax_result = self._check_syntax(cypher)
            if not syntax_result[0]:
                return ValidationResult(
                    is_valid=False,
                    error_type=ErrorType.SYNTAX,
                    error_message=syntax_result[1]
                )
            warnings.extend(syntax_result[2])
        
        # 3. 参数验证
        param_result = self._check_parameters(cypher, parameters)
        if not param_result[0]:
            return ValidationResult(
                is_valid=False,
                error_type=ErrorType.PARAMETER,
                error_message=param_result[1]
            )
        warnings.extend(param_result[2])
        
        # 4. 复杂度检查
        complexity_score = 0
        if self.config.enable_complexity_check:
            complexity_score = self._calculate_complexity(cypher)
            if complexity_score > self.config.max_complexity_score:
                return ValidationResult(
                    is_valid=False,
                    error_type=ErrorType.COMPLEXITY,
                    error_message=f"Query complexity too high: {complexity_score} > {self.config.max_complexity_score}",
                    complexity_score=complexity_score
                )
            elif complexity_score > self.config.max_complexity_score * 0.8:
                warnings.append(f"High complexity query: {complexity_score}")
        
        return ValidationResult(
            is_valid=True,
            warnings=warnings,
            complexity_score=complexity_score
        )
    
    def _check_security(self, cypher: str) -> Tuple[bool, str]:
        """检查安全性
        
        Args:
            cypher: Cypher 查询语句
            
        Returns:
            (is_safe, error_message)
        """
        cypher_upper = cypher.upper()
        
        # 检查危险关键字
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in cypher_upper:
                return False, f"Dangerous operation detected: {keyword}"
        
        # 检查是否只包含安全操作
        # 移除注释和字符串字面量后检查
        cleaned_cypher = self._remove_comments_and_strings(cypher_upper)
        
        # 检查是否以安全的关键字开始
        first_word = cleaned_cypher.split()[0] if cleaned_cypher.split() else ""
        if first_word not in ['MATCH', 'OPTIONAL', 'WITH']:
            return False, f"Query must start with MATCH, OPTIONAL MATCH, or WITH, got: {first_word}"
        
        return True, ""
    
    def _check_syntax(self, cypher: str) -> Tuple[bool, str, List[str]]:
        """检查基础语法
        
        Args:
            cypher: Cypher 查询语句
            
        Returns:
            (is_valid, error_message, warnings)
        """
        warnings = []
        
        # 1. 括号匹配检查
        if not self._check_brackets(cypher):
            return False, "Mismatched brackets", warnings
        
        # 2. 引号匹配检查
        if not self._check_quotes(cypher):
            return False, "Mismatched quotes", warnings
        
        # 3. 基本结构检查
        structure_result = self._check_basic_structure(cypher)
        if not structure_result[0]:
            return False, structure_result[1], warnings
        warnings.extend(structure_result[2])
        
        # 4. 关键字大小写检查（警告）
        if self._has_lowercase_keywords(cypher):
            warnings.append("Consider using uppercase for Cypher keywords")
        
        return True, "", warnings
    
    def _check_brackets(self, cypher: str) -> bool:
        """检查括号匹配"""
        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []
        
        in_string = False
        escape_next = False
        
        for char in cypher:
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char in ['"', "'"]:
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if char in brackets:
                stack.append(char)
            elif char in brackets.values():
                if not stack:
                    return False
                if brackets[stack.pop()] != char:
                    return False
        
        return len(stack) == 0
    
    def _check_quotes(self, cypher: str) -> bool:
        """检查引号匹配"""
        single_quotes = 0
        double_quotes = 0
        escape_next = False
        
        for char in cypher:
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == "'":
                single_quotes += 1
            elif char == '"':
                double_quotes += 1
        
        return single_quotes % 2 == 0 and double_quotes % 2 == 0
    
    def _check_basic_structure(self, cypher: str) -> Tuple[bool, str, List[str]]:
        """检查基本结构"""
        warnings = []
        cypher_upper = cypher.upper()
        
        # 检查必须有 MATCH 或 WITH
        if 'MATCH' not in cypher_upper and 'WITH' not in cypher_upper:
            return False, "Query must contain MATCH or WITH clause", warnings
        
        # 检查必须有 RETURN
        if 'RETURN' not in cypher_upper:
            return False, "Query must contain RETURN clause", warnings
        
        # 检查 RETURN 的位置（应该在查询的末尾部分）
        return_pos = cypher_upper.rfind('RETURN')
        remaining = cypher_upper[return_pos + 6:].strip()
        
        # RETURN 后只应该有列名、ORDER BY、LIMIT、SKIP
        allowed_after_return = ['ORDER BY', 'LIMIT', 'SKIP']
        remaining_words = remaining.split()
        
        i = 0
        while i < len(remaining_words):
            word = remaining_words[i]
            if word in ['ORDER', 'LIMIT', 'SKIP']:
                if word == 'ORDER' and i + 1 < len(remaining_words) and remaining_words[i + 1] == 'BY':
                    i += 2  # Skip "ORDER BY"
                else:
                    i += 1
            elif word.startswith('(') or word.startswith('p.') or word.startswith('n.') or word.isalnum():
                # 可能是列名或表达式
                i += 1
            else:
                # 检查是否是允许的关键字
                found_allowed = False
                for allowed in allowed_after_return:
                    if remaining[i:].upper().startswith(allowed):
                        found_allowed = True
                        break
                if not found_allowed:
                    warnings.append(f"Unexpected keyword after RETURN: {word}")
                i += 1
        
        return True, "", warnings
    
    def _has_lowercase_keywords(self, cypher: str) -> bool:
        """检查是否有小写关键字"""
        keywords = ['match', 'where', 'return', 'with', 'order', 'by', 'limit']
        cypher_lower = cypher.lower()
        
        for keyword in keywords:
            if f' {keyword} ' in cypher_lower or cypher_lower.startswith(f'{keyword} '):
                return True
        
        return False
    
    def _check_parameters(self, cypher: str, parameters: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
        """检查参数"""
        warnings = []
        
        # 提取查询中的参数变量
        param_vars = set(re.findall(r'\$(\w+)', cypher))
        param_keys = set(parameters.keys())
        
        # 检查未提供的参数
        missing_params = param_vars - param_keys
        if missing_params:
            return False, f"Missing parameters: {', '.join(missing_params)}", warnings
        
        # 检查多余的参数
        extra_params = param_keys - param_vars
        if extra_params:
            warnings.append(f"Unused parameters: {', '.join(extra_params)}")
        
        # 检查参数值类型
        for key, value in parameters.items():
            if value is None:
                warnings.append(f"Parameter '{key}' is None")
            elif isinstance(value, str) and not value.strip():
                warnings.append(f"Parameter '{key}' is empty string")
        
        return True, "", warnings
    
    def _calculate_complexity(self, cypher: str) -> int:
        """计算查询复杂度"""
        score = 0
        cypher_upper = cypher.upper()
        
        # 基础分数（减少基础分数）
        score += 1
        
        # MATCH 子句数量（降低权重）
        match_count = cypher_upper.count('MATCH')
        score += match_count * 1  # 从 2 降低到 1
        
        # OPTIONAL MATCH 增加复杂度（降低权重）
        optional_match_count = cypher_upper.count('OPTIONAL MATCH')
        score += optional_match_count * 2  # 从 3 降低到 2
        
        # JOIN 复杂度（通过关系数量估算）
        relationship_count = len(re.findall(r'-\[.*?\]->', cypher))
        score += relationship_count * 1  # 从 2 降低到 1
        
        # WHERE 条件复杂度
        where_count = cypher_upper.count('WHERE')
        score += where_count * 1
        
        # AND/OR 条件（降低 OR 的权重）
        and_count = cypher_upper.count(' AND ')
        or_count = cypher_upper.count(' OR ')
        score += and_count * 1
        score += or_count * 1  # 从 2 降低到 1
        
        # 聚合函数（降低权重）
        aggregations = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX']
        for agg in aggregations:
            score += cypher_upper.count(agg) * 1  # 从 2 降低到 1
        
        # WITH 子句（表示多步查询）
        with_count = cypher_upper.count('WITH')
        score += with_count * 2  # 从 3 降低到 2
        
        # ORDER BY
        if 'ORDER BY' in cypher_upper:
            score += 1
        
        # 嵌套层级（通过括号估算）
        max_nesting = self._calculate_nesting_level(cypher)
        if max_nesting > 3:  # 提高阈值
            score += (max_nesting - 3) * 1  # 降低惩罚
        
        # 不再硬编码最大值限制，由配置管理
        return score
    
    def _calculate_nesting_level(self, cypher: str) -> int:
        """计算嵌套层级"""
        max_level = 0
        current_level = 0
        
        in_string = False
        escape_next = False
        
        for char in cypher:
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char in ['"', "'"]:
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if char == '(':
                current_level += 1
                max_level = max(max_level, current_level)
            elif char == ')':
                current_level = max(0, current_level - 1)
        
        return max_level
    
    def _remove_comments_and_strings(self, cypher: str) -> str:
        """移除注释和字符串字面量"""
        result = []
        in_string = False
        string_char = None
        escape_next = False
        i = 0
        
        while i < len(cypher):
            char = cypher[i]
            
            if escape_next:
                escape_next = False
                if not in_string:
                    result.append(char)
                i += 1
                continue
            
            if char == '\\':
                escape_next = True
                if not in_string:
                    result.append(char)
                i += 1
                continue
            
            if not in_string:
                # 检查行注释
                if char == '/' and i + 1 < len(cypher) and cypher[i + 1] == '/':
                    # 跳过到行尾
                    while i < len(cypher) and cypher[i] != '\n':
                        i += 1
                    continue
                
                # 检查块注释
                if char == '/' and i + 1 < len(cypher) and cypher[i + 1] == '*':
                    # 跳过到 */
                    i += 2
                    while i + 1 < len(cypher):
                        if cypher[i] == '*' and cypher[i + 1] == '/':
                            i += 2
                            break
                        i += 1
                    continue
                
                # 检查字符串开始
                if char in ['"', "'"]:
                    in_string = True
                    string_char = char
                    result.append(' ')  # 用空格替代字符串
                    i += 1
                    continue
                
                result.append(char)
            else:
                # 在字符串中，检查结束
                if char == string_char:
                    in_string = False
                    string_char = None
            
            i += 1
        
        return ''.join(result)
    
    def validate_batch(self, queries: List[Tuple[str, Dict[str, Any]]]) -> List[ValidationResult]:
        """批量验证查询
        
        Args:
            queries: [(cypher, parameters), ...] 列表
            
        Returns:
            ValidationResult 列表
        """
        results = []
        for cypher, parameters in queries:
            result = self.validate(cypher, parameters)
            results.append(result)
        
        return results
    
    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """获取验证结果摘要
        
        Args:
            results: ValidationResult 列表
            
        Returns:
            摘要统计信息
        """
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)
        invalid = total - valid
        
        error_types = {}
        for result in results:
            if not result.is_valid and result.error_type:
                error_type = result.error_type.value
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        avg_complexity = 0
        if total > 0:
            avg_complexity = sum(r.complexity_score for r in results) / total
        
        return {
            "total": total,
            "valid": valid,
            "invalid": invalid,
            "success_rate": valid / total if total > 0 else 0,
            "error_types": error_types,
            "avg_complexity": avg_complexity
        }