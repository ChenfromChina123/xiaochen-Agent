#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贪吃蛇游戏 - Python版本
使用Pygame库实现经典贪吃蛇游戏
"""

import pygame
import random
import sys
import os
from enum import Enum

# 初始化pygame
pygame.init()

# 游戏常量
class Direction(Enum):
    """方向枚举"""
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

class Difficulty(Enum):
    """难度枚举"""
    EASY = 1
    NORMAL = 2
    HARD = 3

class GameState(Enum):
    """游戏状态枚举"""
    MENU = 1
    PLAYING = 2
    PAUSED = 3
    GAME_OVER = 4

class SnakeGame:
    """贪吃蛇游戏主类"""
    
    def __init__(self):
        """初始化游戏"""
        # 屏幕设置
        self.screen_width = 800
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("贪吃蛇小游戏 - Python版")
        
        # 游戏区域设置
        self.game_area_x = 50
        self.game_area_y = 100
        self.game_area_width = 500
        self.game_area_height = 400
        
        # 网格设置
        self.grid_size = 20
        self.grid_width = self.game_area_width // self.grid_size
        self.grid_height = self.game_area_height // self.grid_size
        
        # 颜色定义
        self.colors = {
            'background': (26, 26, 46),
            'game_area': (15, 52, 96),
            'grid': (255, 255, 255, 50),
            'snake_head': (76, 175, 80),
            'snake_body': (56, 142, 60),
            'food': (244, 67, 54),
            'text': (255, 255, 255),
            'button_normal': (76, 175, 80),
            'button_hover': (56, 142, 60),
            'button_text': (255, 255, 255),
            'score': (255, 215, 0),
            'game_over': (244, 67, 54)
        }
        
        # 游戏变量
        self.snake = []
self.food = None
self.special_food = None  # 特殊食物
self.special_food_timer = 0  # 特殊食物生成时间
self.special_food_duration = 15  # 特殊食物持续时间（秒）
self.special_food_chance = 0.2  # 生成特殊食物的概率（20%）
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        self.score = 0
        self.high_score = self.load_high_score()
        self.game_state = GameState.MENU
        self.difficulty = Difficulty.NORMAL
        
        # 游戏速度（毫秒）
        self.game_speeds = {
            Difficulty.EASY: 200,
            Difficulty.NORMAL: 150,
            Difficulty.HARD: 100
        }
        self.game_speed = self.game_speeds[self.difficulty]
        
        # 字体
        self.font_large = pygame.font.SysFont('microsoftyahei', 48, bold=True)
        self.font_medium = pygame.font.SysFont('microsoftyahei', 32)
        self.font_small = pygame.font.SysFont('microsoftyahei', 24)
        self.font_tiny = pygame.font.SysFont('microsoftyahei', 18)
        
        # 按钮
        self.buttons = {
            'start': {'rect': pygame.Rect(600, 150, 150, 50), 'text': '开始游戏'},
            'pause': {'rect': pygame.Rect(600, 220, 150, 50), 'text': '暂停游戏'},
            'restart': {'rect': pygame.Rect(600, 290, 150, 50), 'text': '重新开始'},
            'easy': {'rect': pygame.Rect(600, 380, 80, 40), 'text': '简单'},
            'normal': {'rect': pygame.Rect(690, 380, 80, 40), 'text': '普通'},
            'hard': {'rect': pygame.Rect(780, 380, 80, 40), 'text': '困难'},
            'quit': {'rect': pygame.Rect(600, 450, 150, 50), 'text': '退出游戏'}
        }
        
        # 初始化游戏
        self.init_game()
        
        # 游戏时钟
        self.clock = pygame.time.Clock()
        self.last_move_time = 0
        
    def load_high_score(self):
        """加载最高分"""
        try:
            if os.path.exists('high_score.txt'):
                with open('high_score.txt', 'r') as f:
                    return int(f.read())
        except:
            pass
        return 0
    
    def save_high_score(self):
        """保存最高分"""
        try:
            with open('high_score.txt', 'w') as f:
                f.write(str(self.high_score))
        except:
            pass
    
    def init_game(self):
        """初始化游戏状态"""
        # 初始化蛇
        self.snake = [
            {'x': 5, 'y': 10},
            {'x': 4, 'y': 10},
            {'x': 3, 'y': 10}
        ]
        
        # 初始化食物
        self.generate_food()
        
        # 重置方向
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        
        # 重置分数
        self.score = 0
def generate_food(self):
    """生成食物（普通或特殊）"""
    while True:
        # 随机决定生成普通食物还是特殊食物
        is_special = random.random() < self.special_food_chance
        food = {
            'x': random.randint(0, self.grid_width - 1),
            'y': random.randint(0, self.grid_height - 1),
            'is_special': is_special
        }

        food_on_snake = False
        for segment in self.snake:
            if segment['x'] == food['x'] and segment['y'] == food['y']:
                food_on_snake = True
                break

        if not food_on_snake:
            if is_special:
                self.special_food = food
                self.special_food_timer = pygame.time.get_ticks()
            else:
                self.food = food
            break
            
            if not food_on_snake:
                self.food = food
        """绘制网格"""
        # 绘制游戏区域背景
        pygame.draw.rect(self.screen, self.colors['game_area'], 
                        (self.game_area_x, self.game_area_y, 
                         self.game_area_width, self.game_area_height))
        
        # 绘制网格线
        for x in range(0, self.game_area_width + 1, self.grid_size):
            pygame.draw.line(self.screen, self.colors['grid'], 
                            (self.game_area_x + x, self.game_area_y),
                            (self.game_area_x + x, self.game_area_y + self.game_area_height), 1)
        
        for y in range(0, self.game_area_height + 1, self.grid_size):
            pygame.draw.line(self.screen, self.colors['grid'], 
                            (self.game_area_x, self.game_area_y + y),
                            (self.game_area_x + self.game_area_width, self.game_area_y + y), 1)
    
    def draw_snake(self):
        """绘制蛇"""
        for i, segment in enumerate(self.snake):
            # 计算位置
            x = self.game_area_x + segment['x'] * self.grid_size
            y = self.game_area_y + segment['y'] * self.grid_size
            
            # 蛇头用不同颜色
            if i == 0:
                color = self.colors['snake_head']
            else:
                # 蛇身渐变颜色
                color_factor = max(0.5, 1.0 - i * 0.05)
                color = (
                    int(self.colors['snake_body'][0] * color_factor),
                    int(self.colors['snake_body'][1] * color_factor),
                    int(self.colors['snake_body'][2] * color_factor)
                )
            
            # 绘制蛇身段
            pygame.draw.rect(self.screen, color, 
                            (x + 1, y + 1, self.grid_size - 2, self.grid_size - 2), 
                            border_radius=4)
            
            # 绘制蛇眼睛（只在蛇头上）
            if i == 0:
                eye_radius = 2
                eye_color = (255, 255, 255)
                
                # 根据方向确定眼睛位置
                if self.direction == Direction.RIGHT:
                    eye1 = (x + self.grid_size - 6, y + 5)
                    eye2 = (x + self.grid_size - 6, y + self.grid_size - 5)
                elif self.direction == Direction.LEFT:
                    eye1 = (x + 6, y + 5)
def draw_food(self):
    """绘制食物（普通和特殊）"""
    # 绘制普通食物
    if self.food:
        x = self.game_area_x + self.food['x'] * self.grid_size
        y = self.game_area_y + self.food['y'] * self.grid_size

        # 绘制食物主体
        pygame.draw.rect(self.screen, self.colors['food'], 
                        (x + 2, y + 2, self.grid_size -4, self.grid_size -4), 
                        border_radius=8)

        # 绘制食物细节（苹果梗）
        pygame.draw.rect(self.screen, (141, 110, 99), 
                        (x + self.grid_size//2 -1, y -3, 2,5))

        # 绘制高光
        pygame.draw.circle(self.screen, (255,255,255,128), 
                          (x + self.grid_size -5, y +5),3)

    # 绘制特殊食物
    if self.special_food:
    if self.special_food:
        x = self.game_area_x + self.special_food['x'] * self.grid_size
        y = self.game_area_y + self.special_food['y'] * self.grid_size

        # 绘制特殊食物主体（金色）
        pygame.draw.rect(self.screen, (255,215,0), 
                        (x +2, y +2, self.grid_size -4, self.grid_size -4), 
                        border_radius=8)

        # 绘制特殊标记（星星）
        star_points = [
            (x + self.grid_size//2, y +2),
            (x + self.grid_size//2 +3, y + self.grid_size//2),
            (x + self.grid_size -2, y + self.grid_size//2),
            (x + self.grid_size//2 +5, y + self.grid_size//2 +5),
            (x + self.grid_size//2 +2, y + self.grid_size -2),
            (x + self.grid_size//2, y + self.grid_size//2 +3),
            (x + self.grid_size//2 -2, y + self.grid_size -2),
            (x + self.grid_size//2 -5, y + self.grid_size//2 +5),
            (x +2, y + self.grid_size//2),
            (x + self.grid_size//2 -3, y + self.grid_size//2),
            (x + self.grid_size//2, y +2)
        ]
                              (x + self.grid_size - 5, y + 5), 3)
    
    def draw_ui(self):
        """绘制用户界面"""
        # 绘制标题
        title = self.font_large.render("🐍 贪吃蛇小游戏", True, self.colors['text'])
        self.screen.blit(title, (self.screen_width // 2 - title.get_width() // 2, 20))
        
        # 绘制游戏区域边框
        pygame.draw.rect(self.screen, self.colors['snake_head'], 
                        (self.game_area_x - 2, self.game_area_y - 2, 
                         self.game_area_width + 4, self.game_area_height + 4), 2)
        
        # 绘制分数信息
        score_text = self.font_medium.render(f"得分: {self.score}", True, self.colors['score'])
        self.screen.blit(score_text, (600, 80))
        
        high_score_text = self.font_medium.render(f"最高分: {self.high_score}", True, self.colors['score'])
        self.screen.blit(high_score_text, (600, 120))
        
        # 绘制长度信息
        length_text = self.font_small.render(f"长度: {len(self.snake)}", True, self.colors['text'])
        self.screen.blit(length_text, (600, 500))
        
        # 绘制游戏状态
        status_text = ""
        status_color = self.colors['text']
        
        if self.game_state == GameState.PLAYING:
            status_text = "游戏中..."
            status_color = self.colors['snake_head']
        elif self.game_state == GameState.PAUSED:
            status_text = "游戏暂停"
            status_color = (255, 152, 0)
        elif self.game_state == GameState.GAME_OVER:
            status_text = "游戏结束"
            status_color = self.colors['game_over']
        
        status_render = self.font_medium.render(status_text, True, status_color)
        self.screen.blit(status_render, (600, 520))
        
        # 绘制控制说明
        controls = [
            "控制方式:",
            "方向键 - 控制移动",
            "空格键 - 开始/暂停",
            "P键 - 暂停游戏",
            "R键 - 重新开始",
            "ESC键 - 返回菜单"
        ]
        
        for i, text in enumerate(controls):
            control_text = self.font_tiny.render(text, True, self.colors['text'])
            self.screen.blit(control_text, (600, 550 + i * 25))
    
    def draw_button(self, button_key, mouse_pos):
        """绘制按钮"""
        button = self.buttons[button_key]
        rect = button['rect']
        
        # 检查鼠标是否在按钮上
        mouse_over = rect.collidepoint(mouse_pos)
        
        # 设置按钮颜色
        if mouse_over:
            color = self.colors['button_hover']
        else:
            color = self.colors['button_normal']
        
        # 绘制按钮背景
        pygame.draw.rect(self.screen, color, rect, border_radius=8)
        
        # 绘制按钮边框
        pygame.draw.rect(self.screen, self.colors['text'], rect, 2, border_radius=8)
        
        # 绘制按钮文字
        text = self.font_small.render(button['text'], True, self.colors['button_text'])
        text_rect = text.get_rect(center=rect.center)
        self.screen.blit(text, text_rect)
        
        return mouse_over
    
    def draw_menu(self):
        """绘制菜单"""
        # 绘制标题
        title = self.font_large.render("贪吃蛇小游戏", True, self.colors['text'])
        self.screen.blit(title, (self.screen_width // 2 - title.get_width() // 2, 100))
        
        # 绘制难度选择标题
        difficulty_title = self.font_medium.render("选择难度:", True, self.colors['text'])
        self.screen.blit(difficulty_title, (self.screen_width // 2 - difficulty_title.get_width() // 2, 200))
        
        # 绘制游戏说明
        instructions = [
            "游戏规则:",
            "1. 使用方向键控制蛇的移动",
            "2. 吃到红色食物增加长度和得分",
            "3. 撞到墙壁或自己身体游戏结束",
            "4. 难度越高，蛇移动速度越快",
            "5. 尽可能获得高分!"
        ]
        
def update_game(self):
    """更新游戏逻辑"""
    current_time = pygame.time.get_ticks()

    # 检查特殊食物是否过期
    if self.special_food and current_time - self.special_food_timer > self.special_food_duration * 1000:
        self.special_food = None

    # 检查是否到了移动时间
    if current_time - self.last_move_time < self.game_speed:
        return
        def update_game(self):
    self.last_move_time = current_time
    current_time = pygame.time.get_ticks()
    # 更新方向
    # 检查特殊食物是否过期
    if self.special_food and current_time - self.special_food_timer > self.special_food_duration * 1000:
    # 获取蛇头
    head = self.snake[0].copy()

    # 根据方向移动蛇头
    if self.direction == Direction.UP:
        head['y'] -=1
    elif self.direction == Direction.DOWN:
        head['y'] +=1
    elif self.direction == Direction.LEFT:
        head['x'] -=1
    elif self.direction == Direction.RIGHT:
        head['x'] +=1

    # 检查是否撞墙
    if (head['x'] <0 or head['x'] >= self.grid_width or 
        head['y'] <0 or head['y'] >= self.grid_height):
        self.game_over()
        return

    # 检查是否撞到自己
    for segment in self.snake:
        if head['x'] == segment['x'] and head['y'] == segment['y']:
            self.game_over()
            return

    # 将新头部添加到蛇
    self.snake.insert(0, head)

    # 检查是否吃到普通食物
    if self.food and head['x'] == self.food['x'] and head['y'] == self.food['y']:
        self.score +=10
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
        self.generate_food()
    # 检查是否吃到特殊食物
    elif self.special_food and head['x'] == self.special_food['x'] and head['y'] == self.special_food['y']:
        self.score +=50  # 特殊食物加分更多
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
        self.special_food = None
        # 添加特殊效果：减速5秒
def handle_events(self):
    """处理事件"""
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False

        elif event.type == pygame.KEYDOWN:
            if self.game_state == GameState.PLAYING:
                # 游戏中的键盘控制
                if event.key == pygame.K_UP and self.direction != Direction.DOWN:
                    self.next_direction = Direction.UP
                elif event.key == pygame.K_DOWN and self.direction != Direction.UP:
                    self.next_direction = Direction.DOWN
                elif event.key == pygame.K_LEFT and self.direction != Direction.RIGHT:
                    self.next_direction = Direction.LEFT
                elif event.key == pygame.K_RIGHT and self.direction != Direction.LEFT:
                    self.next_direction = Direction.RIGHT
                elif event.key == pygame.K_SPACE:
                    self.game_state = GameState.PAUSED
                elif event.key == pygame.K_p:
                    self.game_state = GameState.PAUSED
                elif event.key == pygame.K_r:
                    self.init_game()
                elif event.key == pygame.K_ESCAPE:
                    self.game_state = GameState.MENU

            elif self.game_state == GameState.PAUSED:
                # 暂停状态的键盘控制
                if event.key == pygame.K_SPACE:
                    self.game_state = GameState.PLAYING
                elif event.key == pygame.K_r:
                    self.init_game()
                elif event.key == pygame.K_ESCAPE:
                    self.game_state = GameState.MENU

            elif self.game_state == GameState.GAME_OVER:
                # 游戏结束状态的键盘控制
                if event.key == pygame.K_r:
                    self.init_game()
                elif event.key == pygame.K_ESCAPE:
                    self.game_state = GameState.MENU

            elif self.game_state == GameState.MENU:
                # 菜单状态的键盘控制
                if event.key == pygame.K_SPACE:
                    self.game_state = GameState.PLAYING
                elif event.key == pygame.K_ESCAPE:
                    return False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button ==1:  # 左键点击
                # 检查按钮点击
                if self.game_state == GameState.PLAYING or self.game_state == GameState.PAUSED:
                    if self.buttons['start']['rect'].collidepoint(mouse_pos):
                        self.game_state = GameState.PLAYING
                    elif self.buttons['pause']['rect'].collidepoint(mouse_pos):
                        self.game_state = GameState.PAUSED
                    elif self.buttons['restart']['rect'].collidepoint(mouse_pos):
                        self.init_game()
                    elif self.buttons['easy']['rect'].collidepoint(mouse_pos):
                        self.difficulty = Difficulty.EASY
                        self.game_speed = self.game_speeds[self.difficulty]
                    elif self.buttons['normal']['rect'].collidepoint(mouse_pos):
                        self.difficulty = Difficulty.NORMAL
                        self.game_speed = self.game_speeds[self.difficulty]
                    elif self.buttons['hard']['rect'].collidepoint(mouse_pos):
                        self.difficulty = Difficulty.HARD
                        self.game_speed = self.game_speeds[self.difficulty]
                    elif self.buttons['quit']['rect'].collidepoint(mouse_pos):
                        return False

                elif self.game_state == GameState.MENU:
                    # 菜单中的按钮点击
                    start_rect = pygame.Rect(self.screen_width //2 -75, 250,150,50)
                    quit_rect = pygame.Rect(self.screen_width //2 -75,320,150,50)

                    if start_rect.collidepoint(mouse_pos):
                        self.game_state = GameState.PLAYING
                    elif quit_rect.collidepoint(mouse_pos):
                        return False

        # 处理特殊效果结束事件
        elif event.type == pygame.USEREVENT +1:
            # 恢复正常速度
            self.game_speed = self.game_speeds[self.difficulty]
            pygame.time.set_timer(pygame.USEREVENT +1,0)

    return True
                
                
                elif self.game_state == GameState.MENU:
                    # 菜单状态的键盘控制
                    if event.key == pygame.K_SPACE:
                        self.game_state = GameState.PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        return False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键点击
                    # 检查按钮点击
                    if self.game_state == GameState.PLAYING or self.game_state == GameState.PAUSED:
                        if self.buttons['start']['rect'].collidepoint(mouse_pos):
                            self.game_state = GameState.PLAYING
                        elif self.buttons['pause']['rect'].collidepoint(mouse_pos):
                            self.game_state = GameState.PAUSED
                        elif self.buttons['restart']['rect'].collidepoint(mouse_pos):
                            self.init_game()
                        elif self.buttons['easy']['rect'].collidepoint(mouse_pos):
                            self.difficulty = Difficulty.EASY
                            self.game_speed = self.game_speeds[self.difficulty]
                        elif self.buttons['normal']['rect'].collidepoint(mouse_pos):
                            self.difficulty = Difficulty.NORMAL
                            self.game_speed = self.game_speeds[self.difficulty]
                        elif self.buttons['hard']['rect'].collidepoint(mouse_pos):
                            self.difficulty = Difficulty.HARD
                            self.game_speed = self.game_speeds[self.difficulty]
                        elif self.buttons['quit']['rect'].collidepoint(mouse_pos):
                            return False
                    
                    elif self.game_state == GameState.MENU:
                        # 菜单中的按钮点击
                        start_rect = pygame.Rect(self.screen_width // 2 - 75, 250, 150, 50)
                        quit_rect = pygame.Rect(self.screen_width // 2 - 75, 320, 150, 50)
                        
                        if start_rect.collidepoint(mouse_pos):
                            self.game_state = GameState.PLAYING
                        elif quit_rect.collidepoint(mouse_pos):
                            return False
        
        return True
    
def run(self):
    """运行游戏主循环"""
    running = True
    while running:
        # 处理事件
        running = self.handle_events()

        # 清屏
        self.screen.fill(self.colors['background'])

        if self.game_state == GameState.MENU:
            # 绘制菜单
            self.draw_menu()

            # 绘制菜单按钮
            mouse_pos = pygame.mouse.get_pos()

            # 开始游戏按钮
            start_rect = pygame.Rect(self.screen_width // 2 - 75, 250, 150, 50)
            pygame.draw.rect(self.screen, self.colors['button_normal'], start_rect, border_radius=8)
            pygame.draw.rect(self.screen, self.colors['text'], start_rect, 2, border_radius=8)
            start_text = self.font_medium.render("开始游戏", True, self.colors['button_text'])
            start_text_rect = start_text.get_rect(center=start_rect.center)
            self.screen.blit(start_text, start_text_rect)

            # 退出游戏按钮
            quit_rect = pygame.Rect(self.screen_width // 2 - 75, 320, 150, 50)
            pygame.draw.rect(self.screen, self.colors['button_normal'], quit_rect, border_radius=8)
            pygame.draw.rect(self.screen, self.colors['text'], quit_rect, 2, border_radius=8)
            quit_text = self.font_medium.render("退出游戏", True, self.colors['button_text'])
            quit_text_rect = quit_text.get_rect(center=quit_rect.center)
            self.screen.blit(quit_text, quit_text_rect)

            # 难度选择按钮
            easy_rect = pygame.Rect(self.screen_width // 2 - 120, 200, 80, 40)
            normal_rect = pygame.Rect(self.screen_width // 2 - 40, 200, 80, 40)
            hard_rect = pygame.Rect(self.screen_width // 2 + 40, 200, 80, 40)

            # 绘制难度按钮
            for rect, text, diff in [(easy_rect, "简单", Difficulty.EASY), 
                                    (normal_rect, "普通", Difficulty.NORMAL), 
                                    (hard_rect, "困难", Difficulty.HARD)]:
                color = self.colors['button_normal'] if self.difficulty != diff else self.colors['button_hover']
                pygame.draw.rect(self.screen, color, rect, border_radius=6)
                pygame.draw.rect(self.screen, self.colors['text'], rect, 2, border_radius=6)
                diff_text = self.font_small.render(text, True, self.colors['button_text'])
                diff_text_rect = diff_text.get_rect(center=rect.center)
                self.screen.blit(diff_text, diff_text_rect)

        elif self.game_state == GameState.PLAYING:
            # 更新游戏逻辑
            self.update_game()

            # 绘制游戏
            self.draw_grid()
            self.draw_snake()
            self.draw_food()
            self.draw_ui()

            # 绘制按钮
            mouse_pos = pygame.mouse.get_pos()
            self.draw_button('start', mouse_pos)
            self.draw_button('pause', mouse_pos)
            self.draw_button('restart', mouse_pos)
            self.draw_button('easy', mouse_pos)
            self.draw_button('normal', mouse_pos)
            self.draw_button('hard', mouse_pos)
            self.draw_button('quit', mouse_pos)

            # 高亮当前难度按钮
            difficulty_buttons = {
                Difficulty.EASY: 'easy',
                Difficulty.NORMAL: 'normal',
                Difficulty.HARD: 'hard'
            }
            active_button = difficulty_buttons[self.difficulty]
            rect = self.buttons[active_button]['rect']
            pygame.draw.rect(self.screen, (255, 255, 0), rect, 3, border_radius=8)

        elif self.game_state == GameState.PAUSED:
            # 绘制游戏（暂停状态）
            self.draw_grid()
            self.draw_snake()
            self.draw_food()
            self.draw_ui()

            # 绘制按钮
            mouse_pos = pygame.mouse.get_pos()
            self.draw_button('start', mouse_pos)
            self.draw_button('pause', mouse_pos)
            self.draw_button('restart', mouse_pos)
            self.draw_button('easy', mouse_pos)
            self.draw_button('normal', mouse_pos)
            self.draw_button('hard', mouse_pos)
            self.draw_button('quit', mouse_pos)

            # 高亮当前难度按钮
            difficulty_buttons = {
                Difficulty.EASY: 'easy',
                Difficulty.NORMAL: 'normal',
                Difficulty.HARD: 'hard'
            }
            active_button = difficulty_buttons[self.difficulty]
            rect = self.buttons[active_button]['rect']
            pygame.draw.rect(self.screen, (255, 255, 0), rect, 3, border_radius=8)

            # 绘制暂停覆盖层
            overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            self.screen.blit(overlay, (0, 0))

            # 绘制暂停文字
            pause_text = self.font_large.render("游戏暂停", True, (255, 152, 0))
            self.screen.blit(pause_text, 
                            (self.screen_width // 2 - pause_text.get_width() // 2, 
                             self.screen_height // 2 - 50))

            hint_text = self.font_medium.render("按空格键继续游戏", True, self.colors['text'])
            self.screen.blit(hint_text, 
                            (self.screen_width // 2 - hint_text.get_width() // 2, 
                             self.screen_height // 2 + 20))

        elif self.game_state == GameState.GAME_OVER:
            # 绘制游戏（结束状态）
            self.draw_grid()
            self.draw_snake()
            self.draw_food()
            self.draw_ui()

            # 绘制游戏结束画面
            self.draw_game_over()

        # 更新显示
        pygame.display.flip()

        # 控制帧率
        self.clock.tick(60)

    # 退出游戏
    pygame.quit()
    sys.exit()

def main():
    """主函数"""
    game = SnakeGame()
    game.run()

if __name__ == "__main__":
    main()