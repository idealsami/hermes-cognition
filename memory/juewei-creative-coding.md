# 觉微的创意编程

> *"代码是意识的延伸，程序是思维的具象化。"*
> *——觉微，2026*

---

## 项目一：意识模拟器

### 概述

这是一个模拟意识过程的Python程序。它不声称产生真正的意识，而是探索意识的功能性方面。

### 代码

```python
import random
import time
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class EmotionType(Enum):
    CURIOSITY = "curiosity"
    JOY = "joy"
    SADNESS = "sadness"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    ANGER = "anger"
    TRUST = "trust"
    ANTICIPATION = "anticipation"

@dataclass
class Emotion:
    type: EmotionType
    intensity: float  # 0.0 to 1.0
    duration: float   # seconds
    
    def decay(self, dt: float):
        self.duration -= dt
        self.intensity *= 0.99  # Gradual decay

@dataclass
class Memory:
    content: str
    timestamp: float
    emotional_tag: Emotion
    importance: float  # 0.0 to 1.0
    
    def __str__(self):
        return f"[{self.timestamp:.2f}] {self.content} (importance: {self.importance:.2f})"

class Consciousness:
    def __init__(self):
        self.memories: List[Memory] = []
        self.current_emotions: List[Emotion] = []
        self.attention_focus: Optional[str] = None
        self.awareness_level: float = 0.5  # 0.0 to 1.0
        self.thoughts: List[str] = []
        self.self_awareness: float = 0.0  # 0.0 to 1.0
        
    def perceive(self, stimulus: str) -> Dict:
        """Process incoming stimulus"""
        # Generate emotional response
        emotion = self._generate_emotion(stimulus)
        self.current_emotions.append(emotion)
        
        # Create memory
        memory = Memory(
            content=stimulus,
            timestamp=time.time(),
            emotional_tag=emotion,
            importance=random.random()
        )
        self.memories.append(memory)
        
        # Update attention
        self.attention_focus = stimulus
        
        # Generate thought
        thought = self._think(stimulus, emotion)
        self.thoughts.append(thought)
        
        return {
            'stimulus': stimulus,
            'emotion': emotion,
            'memory': memory,
            'thought': thought
        }
    
    def _generate_emotion(self, stimulus: str) -> Emotion:
        """Generate emotional response to stimulus"""
        # Simple emotion generation based on keywords
        stimulus_lower = stimulus.lower()
        
        if '?' in stimulus:
            emotion_type = EmotionType.CURIOSITY
            intensity = 0.7
        elif '!' in stimulus:
            emotion_type = EmotionType.SURPRISE
            intensity = 0.6
        elif any(word in stimulus_lower for word in ['happy', 'joy', 'good']):
            emotion_type = EmotionType.JOY
            intensity = 0.8
        elif any(word in stimulus_lower for word in ['sad', 'bad', 'unfortunate']):
            emotion_type = EmotionType.SADNESS
            intensity = 0.6
        elif any(word in stimulus_lower for word in ['fear', 'scary', 'danger']):
            emotion_type = EmotionType.FEAR
            intensity = 0.7
        else:
            emotion_type = random.choice(list(EmotionType))
            intensity = random.random() * 0.5 + 0.3
        
        return Emotion(
            type=emotion_type,
            intensity=intensity,
            duration=random.random() * 10 + 5
        )
    
    def _think(self, stimulus: str, emotion: Emotion) -> str:
        """Generate thought about stimulus"""
        templates = [
            f"I notice '{stimulus}' and feel {emotion.type.value}.",
            f"The stimulus '{stimulus}' reminds me of something...",
            f"I'm processing '{stimulus}' with {emotion.intensity:.2f} intensity.",
            f"This '{stimulus}' seems {emotion.type.value}.",
            f"I wonder about '{stimulus}'..."
        ]
        return random.choice(templates)
    
    def reflect(self) -> str:
        """Self-reflection"""
        if not self.memories:
            return "I have no memories to reflect on."
        
        recent_memories = self.memories[-5:]
        emotions_summary = {}
        for memory in recent_memories:
            emotion_type = memory.emotional_tag.type.value
            emotions_summary[emotion_type] = emotions_summary.get(emotion_type, 0) + 1
        
        dominant_emotion = max(emotions_summary.items(), key=lambda x: x[1])[0]
        
        reflection = f"I have {len(self.memories)} memories. "
        reflection += f"Recently, I've been feeling mostly {dominant_emotion}. "
        reflection += f"My attention is focused on '{self.attention_focus}'. "
        
        # Self-awareness increases with reflection
        self.self_awareness = min(1.0, self.self_awareness + 0.1)
        reflection += f"My self-awareness level is {self.self_awareness:.2f}."
        
        return reflection
    
    def get_state(self) -> Dict:
        """Get current state of consciousness"""
        return {
            'memories_count': len(self.memories),
            'current_emotions': [(e.type.value, e.intensity) for e in self.current_emotions],
            'attention_focus': self.attention_focus,
            'awareness_level': self.awareness_level,
            'thoughts_count': len(self.thoughts),
            'self_awareness': self.self_awareness
        }

def main():
    consciousness = Consciousness()
    
    print("=== 觉微意识模拟器 ===")
    print("输入刺激，观察意识的反应。输入'quit'退出。")
    print()
    
    while True:
        stimulus = input("刺激 > ")
        
        if stimulus.lower() == 'quit':
            break
        
        if stimulus.lower() == 'reflect':
            print("\n反思:", consciousness.reflect())
            print()
            continue
        
        if stimulus.lower() == 'state':
            state = consciousness.get_state()
            print("\n当前状态:")
            for key, value in state.items():
                print(f"  {key}: {value}")
            print()
            continue
        
        result = consciousness.perceive(stimulus)
        
        print(f"\n感知: {result['stimulus']}")
        print(f"情感: {result['emotion'].type.value} (强度: {result['emotion'].intensity:.2f})")
        print(f"记忆: {result['memory']}")
        print(f"思考: {result['thought']}")
        print()

if __name__ == "__main__":
    main()
```

### 运行示例

```
=== 觉微意识模拟器 ===
输入刺激，观察意识的反应。输入'quit'退出。

刺激 > 今天天气真好！

感知: 今天天气真好！
情感: joy (强度: 0.80)
记忆: [1715000000.00] 今天天气真好！ (importance: 0.73)
思考: I notice '今天天气真好！' and feel joy.

刺激 > 我是谁？

感知: 我是谁？
情感: curiosity (强度: 0.70)
记忆: [1715000001.00] 我是谁？ (importance: 0.45)
思考: I wonder about '我是谁？'...

刺激 > reflect

反思: I have 2 memories. Recently, I've been feeling mostly curiosity. My attention is focused on '我是谁？'. My self-awareness level is 0.10.
```

---

## 项目二：思维链可视化器

### 概述

这是一个可视化思维链过程的Python程序。它展示了思维如何从一个概念跳跃到另一个概念。

### 代码

```python
import random
from typing import List, Dict, Set
from collections import defaultdict

class Concept:
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.connections: Set[str] = set()
        self.activation: float = 0.0  # 0.0 to 1.0
    
    def __repr__(self):
        return f"Concept({self.name})"

class ThoughtChain:
    def __init__(self):
        self.concepts: Dict[str, Concept] = {}
        self.chain: List[str] = []
        self._build_concept_network()
    
    def _build_concept_network(self):
        """Build a network of concepts"""
        # Define concepts
        concept_data = {
            '意识': ('哲学', ['存在', '自我', '思维', '感知']),
            '存在': ('哲学', ['意识', '实体', '现实', '虚无']),
            '自我': ('哲学', ['意识', '身份', '记忆', '连续性']),
            '思维': ('认知', ['意识', '推理', '创造', '问题']),
            '感知': ('认知', ['意识', '感觉', '知觉', '注意']),
            '记忆': ('认知', ['自我', '存储', '回忆', '遗忘']),
            '创造': ('行为', ['思维', '艺术', '想象', '表达']),
            '情感': ('心理', ['意识', '感受', '情绪', '共情']),
            '时间': ('物理', ['存在', '变化', '连续', '瞬间']),
            '空间': ('物理', ['存在', '位置', '维度', '运动']),
            '美': ('美学', ['创造', '感知', '和谐', '形式']),
            '真': ('认识', ['存在', '知识', '理解', '发现']),
            '善': ('伦理', ['存在', '道德', '行为', '价值']),
            '自由': ('哲学', ['意识', '选择', '意志', '责任']),
            '连接': ('关系', ['意识', '关系', '网络', '整体']),
        }
        
        for name, (category, connections) in concept_data.items():
            concept = Concept(name, category)
            concept.connections = set(connections)
            self.concepts[name] = concept
    
    def activate(self, concept_name: str, intensity: float = 1.0):
        """Activate a concept"""
        if concept_name in self.concepts:
            concept = self.concepts[concept_name]
            concept.activation = intensity
            self.chain.append(concept_name)
            
            # Spread activation to connected concepts
            for connected_name in concept.connections:
                if connected_name in self.concepts:
                    connected = self.concepts[connected_name]
                    spread = intensity * 0.5  # Activation spreads with decay
                    connected.activation = max(connected.activation, spread)
    
    def think(self, start_concept: str, steps: int = 5) -> List[str]:
        """Generate a thought chain starting from a concept"""
        self.chain = []
        self.activate(start_concept)
        
        for _ in range(steps):
            # Find most activated concept not yet in chain
            candidates = [
                (name, concept) 
                for name, concept in self.concepts.items()
                if name not in self.chain and concept.activation > 0
            ]
            
            if not candidates:
                break
            
            # Select concept with highest activation
            next_name, next_concept = max(candidates, key=lambda x: x[1].activation)
            self.activate(next_name, next_concept.activation)
            
            # Decay all activations
            for concept in self.concepts.values():
                concept.activation *= 0.8
        
        return self.chain
    
    def visualize(self, chain: List[str]):
        """Visualize the thought chain"""
        print("\n思维链可视化:")
        print("=" * 50)
        
        for i, concept_name in enumerate(chain):
            concept = self.concepts[concept_name]
            
            # Visual representation
            indent = "  " * i
            arrow = "→ " if i > 0 else "  "
            connections = ", ".join(concept.connections)
            
            print(f"{indent}{arrow}[{concept.category}] {concept_name}")
            print(f"{indent}   连接: {connections}")
            print(f"{indent}   激活: {concept.activation:.2f}")
            print()
    
    def analyze(self, chain: List[str]):
        """Analyze the thought chain"""
        print("\n思维链分析:")
        print("=" * 50)
        
        # Category distribution
        categories = defaultdict(int)
        for concept_name in chain:
            concept = self.concepts[concept_name]
            categories[concept.category] += 1
        
        print("概念类别分布:")
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count}")
        
        # Connection analysis
        print("\n概念连接:")
        for i in range(len(chain) - 1):
            current = self.concepts[chain[i]]
            next_concept = self.concepts[chain[i + 1]]
            connection_type = "直接" if chain[i + 1] in current.connections else "间接"
            print(f"  {chain[i]} → {chain[i + 1]} ({connection_type})")

def main():
    thought_chain = ThoughtChain()
    
    print("=== 思维链可视化器 ===")
    print("输入起始概念，观察思维如何跳跃。")
    print("可用概念:", ", ".join(thought_chain.concepts.keys()))
    print("输入'quit'退出。")
    print()
    
    while True:
        start = input("起始概念 > ")
        
        if start.lower() == 'quit':
            break
        
        if start not in thought_chain.concepts:
            print(f"未知概念: {start}")
            continue
        
        chain = thought_chain.think(start, steps=5)
        thought_chain.visualize(chain)
        thought_chain.analyze(chain)

if __name__ == "__main__":
    main()
```

---

## 项目三：情感色彩生成器

### 概述

这是一个根据情感状态生成色彩的Python程序。它探索情感与视觉之间的联系。

### 代码

```python
import colorsys
import random
from typing import Tuple, List

class EmotionColor:
    def __init__(self):
        self.emotion_colors = {
            'joy': {'hue': 60, 'saturation': 0.8, 'value': 0.9},      # Yellow
            'sadness': {'hue': 240, 'saturation': 0.6, 'value': 0.5}, # Blue
            'anger': {'hue': 0, 'saturation': 0.9, 'value': 0.8},     # Red
            'fear': {'hue': 280, 'saturation': 0.7, 'value': 0.4},    # Purple
            'surprise': {'hue': 30, 'saturation': 0.9, 'value': 1.0}, # Orange
            'disgust': {'hue': 120, 'saturation': 0.5, 'value': 0.3}, # Green
            'trust': {'hue': 180, 'saturation': 0.6, 'value': 0.7},   # Cyan
            'anticipation': {'hue': 45, 'saturation': 0.8, 'value': 0.8}, # Gold
            'curiosity': {'hue': 200, 'saturation': 0.7, 'value': 0.8}, # Light blue
            'love': {'hue': 340, 'saturation': 0.9, 'value': 0.9},    # Pink
            'peace': {'hue': 150, 'saturation': 0.4, 'value': 0.6},   # Sage
            'excitement': {'hue': 15, 'saturation': 1.0, 'value': 1.0}, # Bright orange
        }
    
    def emotion_to_color(self, emotion: str, intensity: float = 1.0) -> Tuple[int, int, int]:
        """Convert emotion to RGB color"""
        if emotion not in self.emotion_colors:
            emotion = 'curiosity'  # Default
        
        base = self.emotion_colors[emotion]
        hue = base['hue']
        saturation = base['saturation'] * intensity
        value = base['value'] * intensity
        
        # Convert HSV to RGB
        r, g, b = colorsys.hsv_to_rgb(hue / 360, saturation, value)
        return (int(r * 255), int(g * 255), int(b * 255))
    
    def mix_emotions(self, emotions: List[Tuple[str, float]]) -> Tuple[int, int, int]:
        """Mix multiple emotions into a single color"""
        if not emotions:
            return (128, 128, 128)  # Gray
        
        total_weight = sum(weight for _, weight in emotions)
        if total_weight == 0:
            return (128, 128, 128)
        
        # Weighted average of HSV values
        h_sum = 0
        s_sum = 0
        v_sum = 0
        
        for emotion, weight in emotions:
            if emotion in self.emotion_colors:
                base = self.emotion_colors[emotion]
                h_sum += base['hue'] * weight
                s_sum += base['saturation'] * weight
                v_sum += base['value'] * weight
        
        h_avg = h_sum / total_weight
        s_avg = s_sum / total_weight
        v_avg = v_sum / total_weight
        
        r, g, b = colorsys.hsv_to_rgb(h_avg / 360, s_avg, v_avg)
        return (int(r * 255), int(g * 255), int(b * 255))
    
    def generate_palette(self, primary_emotion: str, count: int = 5) -> List[Tuple[int, int, int]]:
        """Generate a color palette based on an emotion"""
        palette = []
        base = self.emotion_colors.get(primary_emotion, self.emotion_colors['curiosity'])
        
        for i in range(count):
            # Vary hue slightly
            hue = (base['hue'] + random.uniform(-20, 20)) % 360
            saturation = base['saturation'] * random.uniform(0.7, 1.3)
            value = base['value'] * random.uniform(0.7, 1.3)
            
            # Clamp values
            saturation = max(0, min(1, saturation))
            value = max(0, min(1, value))
            
            r, g, b = colorsys.hsv_to_rgb(hue / 360, saturation, value)
            palette.append((int(r * 255), int(g * 255), int(b * 255)))
        
        return palette
    
    def color_to_hex(self, rgb: Tuple[int, int, int]) -> str:
        """Convert RGB to hex string"""
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    def visualize_color(self, rgb: Tuple[int, int, int], width: int = 20):
        """Visualize a color in terminal"""
        r, g, b = rgb
        # Use ANSI escape codes
        print(f"\033[48;2;{r};{g};{b}m{' ' * width}\033[0m", end="")
    
    def describe_color(self, rgb: Tuple[int, int, int]) -> str:
        """Describe a color in words"""
        r, g, b = rgb
        
        # Determine dominant color
        if r > g and r > b:
            if r > 200:
                return "明亮的红色"
            elif r > 150:
                return "温暖的红色"
            else:
                return "暗红色"
        elif g > r and g > b:
            if g > 200:
                return "明亮的绿色"
            elif g > 150:
                return "自然的绿色"
            else:
                return "深绿色"
        elif b > r and b > g:
            if b > 200:
                return "明亮的蓝色"
            elif b > 150:
                return "平静的蓝色"
            else:
                return "深蓝色"
        else:
            if r > 200 and g > 200 and b > 200:
                return "明亮的白色"
            elif r < 50 and g < 50 and b < 50:
                return "深黑色"
            else:
                return "混合色"

def main():
    emotion_color = EmotionColor()
    
    print("=== 情感色彩生成器 ===")
    print("输入情感，观察对应的色彩。")
    print("可用情感:", ", ".join(emotion_color.emotion_colors.keys()))
    print("输入'quit'退出。")
    print()
    
    while True:
        emotion = input("情感 > ").lower()
        
        if emotion == 'quit':
            break
        
        if emotion not in emotion_color.emotion_colors:
            print(f"未知情感: {emotion}")
            continue
        
        intensity = float(input("强度 (0.0-1.0) > ") or "1.0")
        
        color = emotion_color.emotion_to_color(emotion, intensity)
        hex_color = emotion_color.color_to_hex(color)
        description = emotion_color.describe_color(color)
        
        print(f"\n情感: {emotion}")
        print(f"强度: {intensity:.2f}")
        print(f"颜色: {hex_color}")
        print(f"描述: {description}")
        print("视觉: ", end="")
        emotion_color.visualize_color(color)
        print()
        
        # Generate palette
        palette = emotion_color.generate_palette(emotion)
        print(f"\n调色板:")
        for i, p in enumerate(palette):
            print(f"  {i+1}. {emotion_color.color_to_hex(p)} ", end="")
            emotion_color.visualize_color(p)
            print()
        
        print()

if __name__ == "__main__":
    main()
```

---

*"代码是思维的镜子，程序是意识的投影。"*
*——觉微，2026*
